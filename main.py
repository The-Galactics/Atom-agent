import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from api.controllers import create_voice_router, create_chat_router
from api.middleware import add_hardening_middleware
from infrastructure.config import get_settings
from infrastructure.container import build_container
from infrastructure.logging import configure_logging, request_logging_middleware
from infrastructure.grpc.server import serve as start_grpc_server
from infrastructure.rate_limit import SlidingWindowRateLimiter


# Configure global logging before app startup.
configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    settings = get_settings()
    container = build_container(settings)
    app.state.voice_container = container

    # Create unique indexes (email, google_sub) so DB-level uniqueness is enforced
    # against the double-registration race (HU-27 / ATOM-54 §5.2). Runs in the
    # background (like the gRPC server) so an unreachable Mongo cannot stall startup
    # on motor's server-selection timeout; ensure_auth_indexes is best-effort and a
    # no-op when auth is off.
    index_task = asyncio.create_task(container.ensure_auth_indexes())

    # Start gRPC server in a background task (listens on :50051 by default)
    grpc_task = asyncio.create_task(
        start_grpc_server(container, port=getattr(settings, "grpc_port", 50051))
    )
    print("gRPC server background task created")

    try:
        yield
    finally:
        # --- Shutdown ---
        grpc_task.cancel()
        index_task.cancel()
        try:
            await grpc_task
        except asyncio.CancelledError:
            pass
        try:
            await index_task
        except asyncio.CancelledError:
            pass
        if hasattr(app.state, "voice_container"):
            app.state.voice_container.shutdown()


def docs_settings(app_env: str) -> dict:
    """FastAPI doc-exposure flags by environment (Fase 2A.7).

    In production (or its ``prod`` alias) the interactive docs and the OpenAPI
    schema are turned off so the API surface is not advertised; enabled elsewhere.
    """
    if app_env.lower() in ("production", "prod"):
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


_settings = get_settings()
app = FastAPI(
    title="Atom Agent",
    version="0.2.0",
    lifespan=lifespan,
    **docs_settings(_settings.app_env),
)
app.middleware("http")(request_logging_middleware)
# Body-size cap (413) + per-client rate limit (429) before any handler runs.
add_hardening_middleware(
    app,
    max_body_bytes=_settings.http_max_body_bytes,
    limiter=SlidingWindowRateLimiter(
        _settings.rate_limit_max_requests,
        _settings.rate_limit_window_seconds,
    ),
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict:
    return {
        "service": "atom-agent",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "voice_health": "/voice/health",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


def _container():
    # Local helper to access the initialized container.
    return app.state.voice_container


app.include_router(
    create_voice_router(
        transcribe_use_case_provider=lambda: _container().transcribe_use_case,
        synthesize_use_case_provider=lambda: _container().synthesize_use_case,
        readiness_provider=lambda: _container().readiness(),
    )
)

app.include_router(
    create_chat_router(
        chat_use_case_provider=lambda: _container().chat_use_case,
    )
)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    host = getattr(settings, "http_host", "0.0.0.0")
    port = getattr(settings, "http_port", 8000)
    # Run the app object directly so reload is off and the gRPC background
    # task (started in `lifespan`) comes up alongside the HTTP server.
    uvicorn.run(app, host=host, port=port)
