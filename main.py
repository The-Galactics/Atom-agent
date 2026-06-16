import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from api.controllers import create_voice_router, create_chat_router
from infrastructure.config import get_settings
from infrastructure.container import build_container
from infrastructure.logging import configure_logging, request_logging_middleware
from infrastructure.grpc.server import serve as start_grpc_server


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    settings = get_settings()
    container = build_container(settings)
    app.state.voice_container = container

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
        try:
            await grpc_task
        except asyncio.CancelledError:
            pass
        if hasattr(app.state, "voice_container"):
            app.state.voice_container.shutdown()


app = FastAPI(title="Atom Agent", version="0.2.0", lifespan=lifespan)
app.middleware("http")(request_logging_middleware)


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
