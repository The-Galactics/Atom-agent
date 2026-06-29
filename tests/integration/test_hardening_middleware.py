import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.middleware import add_hardening_middleware
from infrastructure.rate_limit import SlidingWindowRateLimiter


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _app(*, limiter=None, max_body_bytes=10_000):
    app = FastAPI()

    @app.post("/echo")
    async def echo(payload: dict):
        return {"ok": True}

    add_hardening_middleware(
        app,
        max_body_bytes=max_body_bytes,
        limiter=limiter or SlidingWindowRateLimiter(100, 60),
    )
    return app


@pytest.mark.anyio
async def test_rate_limit_returns_429_after_limit():
    app = _app(limiter=SlidingWindowRateLimiter(max_requests=2, window_seconds=60))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        assert (await c.post("/echo", json={})).status_code == 200
        assert (await c.post("/echo", json={})).status_code == 200
        blocked = await c.post("/echo", json={})
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "RATE_LIMITED"


@pytest.mark.anyio
async def test_body_over_limit_returns_413():
    app = _app(max_body_bytes=10)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/echo", json={"x": "y" * 500})
        assert r.status_code == 413
        assert r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


@pytest.mark.anyio
async def test_request_within_limits_passes_through():
    app = _app(max_body_bytes=10_000, limiter=SlidingWindowRateLimiter(5, 60))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/echo", json={"hello": "world"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}
