"""Unit tests for the current-date context injected into LLM prompts.

The sentence must state the real present date/time in Spanish so the model
answers date questions deterministically instead of guessing at training time.
"""

import re
from datetime import datetime, timedelta, timezone

from domain.datetime_context import current_datetime_sentence, _DAYS, _MONTHS


def test_sentence_contains_real_current_date():
    # Compare against the same UTC-5 (Colombia) clock the module uses by default.
    now = datetime.now(timezone(timedelta(hours=-5)))
    sentence = current_datetime_sentence("America/Bogota")
    assert str(now.day) in sentence
    assert _MONTHS[now.month - 1] in sentence
    assert str(now.year) in sentence
    assert _DAYS[now.weekday()] in sentence


def test_sentence_includes_24h_time_and_timezone_label():
    sentence = current_datetime_sentence("America/Bogota")
    # HH:MM in 24h form, plus the explicit Colombia/UTC-5 label.
    assert re.search(r"\b\d{2}:\d{2}\b", sentence)
    assert "UTC-5" in sentence


def test_sentence_is_in_spanish_and_grounding_oriented():
    sentence = current_datetime_sentence("America/Bogota")
    assert "Fecha y hora actuales" in sentence


def test_unknown_timezone_falls_back_without_raising():
    # An invalid IANA name must not raise; it falls back to the Colombia offset.
    sentence = current_datetime_sentence("Not/AZone")
    assert "UTC-5" in sentence
    assert "Fecha y hora actuales" in sentence
