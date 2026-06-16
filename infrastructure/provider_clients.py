from __future__ import annotations

import time
from dataclasses import dataclass

import requests
from domain.errors import ProviderError


@dataclass(frozen=True)
class KokoroClientConfig:
    # Immutable HTTP client configuration.
    endpoint: str
    api_key: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 2
    retry_backoff_seconds: float = 0.25
    model: str = "kokoro"


class KokoroClient:
    # Simple HTTP client for the TTS provider (Kokoro).
    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.25,
        model: str = "kokoro",
    ) -> None:
        self._config = KokoroClientConfig(
            endpoint=endpoint.rstrip("/"),
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            model=model,
        )
        self._session = requests.Session()

    def synthesize(
        self,
        text: str,
        voice: str,
        audio_format: str,
        language: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        # Send synthesis request and return raw audio bytes.
        # Kokoro FastAPI deployments commonly expose an OpenAI-compatible
        # /v1/audio/speech endpoint. KOKORO_ENDPOINT should point to that full URL.
        payload = {
            "model": self._config.model,
            "input": text,
            "voice": voice,
            "response_format": audio_format,
            "speed": speed,
        }
        if language:
            payload["language"] = language

        headers = {
            "Content-Type": "application/json",
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        last_error: Exception | None = None
        # Retry transient HTTP errors with exponential backoff.
        for attempt in range(self._config.max_retries + 1):
            try:
                response = self._session.post(
                    self._config.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self._config.timeout_seconds,
                )
                response.raise_for_status()
                if not response.content:
                    raise ProviderError("Kokoro returned an empty audio response.")
                return response.content
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self._config.max_retries:
                    break
                time.sleep(self._config.retry_backoff_seconds * (2**attempt))

        raise ProviderError(f"Kokoro HTTP request failed: {last_error}") from last_error

    def health(self) -> bool:
        # Lightweight provider availability probe.
        try:
            response = self._session.get(
                self._config.endpoint,
                headers={"Authorization": f"Bearer {self._config.api_key}"} if self._config.api_key else None,
                timeout=min(self._config.timeout_seconds, 5),
            )
            return response.status_code < 500
        except requests.RequestException:
            return False
