"""Deterministic yes/no classifier for the conversational confirmation flow.

When the agent proposes a sensitive action it asks the user to confirm; the
user's spoken reply ("sí" / "no" / something ambiguous) is classified here
*without* a second LLM call — deterministic, zero-latency and fully testable.
Multilingual (Spanish/English). Returns ``"unclear"`` rather than guessing so
the orchestrator can re-ask instead of acting on a misread.
"""

from __future__ import annotations

import unicodedata
from typing import Literal

Verdict = Literal["yes", "no", "unclear"]

# Affirmative / negative tokens, accent-stripped and lowercased (see _normalize).
_YES = frozenset({
    "si", "sip", "claro", "vale", "dale", "ok", "okay", "oka", "correcto",
    "adelante", "hazlo", "hagalo", "confirmo", "confirmar", "perfecto", "eso",
    "exacto", "afirmativo", "procede", "continua", "acepto", "bueno",
    "yes", "yeah", "yep", "yup", "sure", "okey", "confirm", "confirmed",
    "proceed", "affirmative", "correct",
})
_NO = frozenset({
    "no", "nop", "nope", "cancela", "cancelar", "para", "parar", "detente",
    "detener", "alto", "negativo", "nunca", "rechazo", "rechazar", "olvidalo",
    "cancel", "stop", "dont", "nevermind", "abort", "negative", "deny",
})
# Uncertainty phrases — evaluated FIRST so e.g. "no sé" (I don't know) isn't
# misread as a rejection just because it contains the token "no".
_UNCLEAR_PHRASES = (
    "no se", "no lo se", "no estoy seguro", "no estoy segura", "ni idea",
    "tal vez", "quizas", "no sabria", "puede ser",
    "not sure", "i dont know", "dont know", "dunno", "maybe", "perhaps",
)
# Negative multi-word phrases checked before single-token logic.
_NO_PHRASES = ("mejor no", "no lo hagas", "no gracias", "dont do", "do not", "no quiero")
_YES_PHRASES = ("hazlo ya", "si por favor", "go ahead", "do it", "sounds good", "esta bien")


def _normalize(text: str) -> str:
    """Lowercase, strip accents, and reduce to alphanumerics + single spaces.

    Dropping punctuation (apostrophes, periods…) makes phrase matching robust:
    "i don't know." and "no sé," both normalize to forms the phrase/token sets
    recognize.
    """
    folded = unicodedata.normalize("NFKD", text or "").casefold()
    no_accents = "".join(c for c in folded if not unicodedata.combining(c))
    cleaned = "".join(c if c.isalnum() else " " for c in no_accents)
    return " ".join(cleaned.split())


def _tokens(normalized: str) -> list[str]:
    return ["".join(c for c in tok if c.isalnum()) for tok in normalized.split()]


def classify_affirmation(text: str) -> Verdict:
    """Classify a reply as ``"yes"``, ``"no"`` or ``"unclear"``.

    Phrases win over single tokens; if both an affirmative and a negative token
    appear (e.g. "sí pero no"), the result is ``"unclear"`` to force a re-ask.
    """
    normalized = _normalize(text)
    if not normalized:
        return "unclear"

    if any(phrase in normalized for phrase in _UNCLEAR_PHRASES):
        return "unclear"
    if any(phrase in normalized for phrase in _NO_PHRASES):
        return "no"
    if any(phrase in normalized for phrase in _YES_PHRASES):
        return "yes"

    tokens = [tok for tok in _tokens(normalized) if tok]
    has_yes = any(tok in _YES for tok in tokens)
    has_no = any(tok in _NO for tok in tokens)

    if has_yes and not has_no:
        return "yes"
    if has_no and not has_yes:
        return "no"
    return "unclear"
