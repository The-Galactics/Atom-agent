"""Heuristic, dependency-free rules deciding whether a chat turn is worth
persisting to long-term semantic memory.

Keeping junk out at write time is cheaper and more effective than pruning it
later: most conversational turns (greetings, acknowledgements, smalltalk) carry
no durable information and only dilute semantic search. These rules are
intentionally simple (no LLM call) so they add no latency or cost per turn.
"""

import re

# Short, low-signal utterances we never store on their own.
_TRIVIAL = {
    "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    "ok", "okay", "vale", "listo", "gracias", "muchas gracias", "adios",
    "chao", "si", "no", "claro", "perfecto", "genial", "hey", "hello",
    "hi", "que tal", "como estas", "bien", "jaja", "jajaja", "test",
}

# First-person / instruction markers that signal a fact worth remembering.
_FACT_MARKERS = (
    "me llamo", "mi nombre", "soy ", "tengo ", "mi ", "vivo", "trabajo",
    "estudio", "favorit", "prefier", "odio", "me gusta", "no me gusta",
    "recuerda", "no olvides", "acuerdate", "mi cumple", "naci",
)


def is_memorable(user_text: str, min_words: int = 4) -> bool:
    """Return True if ``user_text`` is worth storing in semantic memory.

    A turn is memorable when it either contains an explicit fact/instruction
    marker, or carries enough substance (>= ``min_words``). Trivial greetings
    and acknowledgements are rejected.
    """
    text = (user_text or "").strip().lower()
    if not text:
        return False
    # Normalize (drop punctuation/accents-insensitive lookup is out of scope).
    normalized = re.sub(r"[^\w\s]", "", text).strip()
    if normalized in _TRIVIAL:
        return False
    # Explicit fact / instruction markers always win.
    if any(marker in text for marker in _FACT_MARKERS):
        return True
    # Otherwise require some substance to avoid storing tiny smalltalk.
    return len(normalized.split()) >= min_words
