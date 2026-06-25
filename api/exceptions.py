"""API-layer error sanitization (Fase 2A.1 / US-10.1, lado HTTP).

Client-facing errors are reduced to a generic, code-keyed message plus a
``request_id``. The real exception text (stack/cause) is written only to the
server logs, never echoed back to the client.
"""

import logging
import uuid

logger = logging.getLogger(__name__)


class ApiError(Exception):
    # Base exception type for API-layer errors.
    pass


# Client-facing messages. Keyed by a stable, non-sensitive code. Anything not in
# this table degrades to INTERNAL so we never leak an unmapped internal detail.
GENERIC_MESSAGES = {
    "INTERNAL": "Internal server error occurred",
    "CHAT_UNAVAILABLE": "Chat service is temporarily unavailable",
    "VOICE_UNAVAILABLE": "Voice service is temporarily unavailable",
    "RATE_LIMITED": "Too many requests, please slow down",
    "PAYLOAD_TOO_LARGE": "Request payload is too large",
}


def generic_message(code: str) -> str:
    """Return the client-safe message for ``code``, falling back to INTERNAL."""
    return GENERIC_MESSAGES.get(code, GENERIC_MESSAGES["INTERNAL"])


def new_request_id() -> str:
    """A unique, non-guessable correlation id to tie a client error to its log."""
    return uuid.uuid4().hex


def grpc_internal_detail(request_id: str) -> str:
    """Client-facing gRPC detail: carries only the request_id, never exc text."""
    return f"{GENERIC_MESSAGES['INTERNAL']} (request_id={request_id})"


def log_exception(code: str, request_id: str, exc: BaseException, *, context: str) -> None:
    """Record the full exception detail server-side (ops only), correlated by
    ``request_id``. This is the single place the real cause is allowed to surface."""
    logger.error(
        "[%s] %s failed (request_id=%s): %s",
        code,
        context,
        request_id,
        exc,
        exc_info=exc,
    )
