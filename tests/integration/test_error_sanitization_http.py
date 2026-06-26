"""HTTP error sanitization (US-10.1, HTTP side): 5xx server-side errors must not
echo the raw exception text; the client gets a generic message + a request_id,
while the real cause is logged server-side. 4xx validation feedback is preserved.
"""

import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.controllers import create_chat_router
from domain.errors import DomainError, DomainValidationError, ProviderError


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _RaisingChat:
    def __init__(self, exc):
        self._exc = exc

    async def execute(self, _dto):
        raise self._exc


def _app(exc):
    app = FastAPI()
    app.include_router(create_chat_router(_RaisingChat(exc)))
    return app


async def _post_chat(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.post("/chat", json={"text": "hola"})


@pytest.mark.anyio
async def test_provider_error_is_sanitized(caplog):
    app = _app(ProviderError("secret provider dsn leaked"))
    with caplog.at_level(logging.ERROR):
        r = await _post_chat(app)
    assert r.status_code == 503
    body = r.json()
    assert "secret provider dsn leaked" not in str(body)  # not echoed to client
    assert body["detail"]["error"]["request_id"]           # correlation id present
    assert "secret provider dsn leaked" in caplog.text     # real cause logged


@pytest.mark.anyio
async def test_domain_error_is_sanitized(caplog):
    app = _app(DomainError("internal invariant boom"))
    with caplog.at_level(logging.ERROR):
        r = await _post_chat(app)
    assert r.status_code == 500
    body = r.json()
    assert "internal invariant boom" not in str(body)
    assert body["detail"]["error"]["request_id"]
    assert "internal invariant boom" in caplog.text


@pytest.mark.anyio
async def test_validation_error_message_is_preserved():
    # 4xx validation feedback is intentional and must still reach the client.
    app = _app(DomainValidationError("text must not be blank"))
    r = await _post_chat(app)
    assert r.status_code == 400
    assert "text must not be blank" in str(r.json())
