"""Current-date context for LLM prompts.

An LLM has no clock: its knowledge is frozen at training time, so when asked
"what day is it?" it answers with a stale guess. Web grounding does not fix this
reliably either. The deterministic fix is to inject the *real* current date and
time (in the assistant's configured timezone) into the system prompt on every
turn — zero cost, zero latency, always correct.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

try:  # zoneinfo is stdlib on 3.9+, but the IANA database may be absent in slim
    from zoneinfo import ZoneInfo  # containers — hence the `tzdata` requirement.
except ImportError:  # pragma: no cover - very old runtimes
    ZoneInfo = None

# Spanish day/month names, hardcoded so we don't depend on a system locale
# (es_CO is usually not installed in the API container).
_DAYS = (
    "lunes", "martes", "miércoles", "jueves",
    "viernes", "sábado", "domingo",
)
_MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

# Colombia is UTC-5 year-round (no DST); used as the fallback offset when the
# IANA tz database is unavailable so the time is still right for the default tz.
_COLOMBIA_FALLBACK = timezone(timedelta(hours=-5))


def _now(tz_name: str) -> datetime:
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(tz_name))
        except Exception:
            pass
    return datetime.now(_COLOMBIA_FALLBACK)


def current_datetime_sentence(tz_name: str = "America/Bogota") -> str:
    """A short Spanish sentence stating the current date and time.

    Prepend it to the system prompt so the model answers date/time questions
    with the real present instead of a training-time guess.
    """
    now = _now(tz_name)
    day = _DAYS[now.weekday()]
    month = _MONTHS[now.month - 1]
    return (
        "Fecha y hora actuales (esta es la realidad presente; úsala para "
        "cualquier pregunta sobre la fecha, el día u hora): "
        f"{day} {now.day} de {month} de {now.year}, {now.hour:02d}:{now.minute:02d} "
        "(hora de Colombia, UTC-5)."
    )
