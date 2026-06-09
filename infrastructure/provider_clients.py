import requests
from domain.errors import ProviderError


class KokoroClient:
    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def synthesize(
        self,
        text: str,
        voice: str,
        audio_format: str,
        language: str | None = None,
    ) -> bytes:
        payload = {
            "text": text,
            "voice": voice,
            "format": audio_format,
        }
        if language:
            payload["language"] = language

        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = requests.post(
                self._endpoint,
                json=payload,
                headers=headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            raise ProviderError(f"Kokoro HTTP request failed: {exc}") from exc
