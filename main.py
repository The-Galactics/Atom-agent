from fastapi import FastAPI, Response

from api.controllers import create_voice_router, create_chat_router
from infrastructure.config import get_settings
from infrastructure.container import build_container
from infrastructure.logging import configure_logging, request_logging_middleware


configure_logging()

app = FastAPI(title="Atom Agent", version="0.2.0")
app.middleware("http")(request_logging_middleware)


@app.on_event("startup")
def startup_event() -> None:
    app.state.voice_container = build_container(get_settings())


@app.on_event("shutdown")
def shutdown_event() -> None:
    if hasattr(app.state, "voice_container"):
        app.state.voice_container.shutdown()


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
