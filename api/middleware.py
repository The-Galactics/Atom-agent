"""HTTP hardening middleware (Fase 2A.3): body-size cap + per-client rate limit."""

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from api.exceptions import generic_message, new_request_id
from infrastructure.rate_limit import SlidingWindowRateLimiter


def _client_key(request: Request) -> str:
    # Prefer the original client when behind a proxy, else the socket peer.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "anon"


def _error_response(code: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": generic_message(code),
                "request_id": new_request_id(),
            }
        },
    )


def add_hardening_middleware(
    app: FastAPI,
    *,
    max_body_bytes: int,
    limiter: SlidingWindowRateLimiter | None,
) -> None:
    """Register a middleware that rejects oversized bodies (413) and throttles
    clients past the rate limit (429) before the request reaches a handler."""

    @app.middleware("http")
    async def _hardening(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > max_body_bytes:
                    return _error_response("PAYLOAD_TOO_LARGE", 413)
            except ValueError:
                pass  # malformed header — let the framework handle the body
        if limiter is not None and not limiter.allow(_client_key(request)):
            return _error_response("RATE_LIMITED", 429)
        return await call_next(request)
