"""Unit tests for the memory-importance heuristic (``is_memorable``)."""

from domain.memory.importance import is_memorable


def test_empty_text_is_not_memorable():
    assert is_memorable("") is False
    assert is_memorable("   ") is False
    assert is_memorable(None) is False


def test_trivial_greetings_are_not_memorable():
    for trivial in ("hola", "Gracias", "ok", "buenos dias", "jajaja"):
        assert is_memorable(trivial) is False


def test_punctuation_is_normalized_before_trivial_check():
    # "¡Hola!" normalizes to "hola" -> trivial.
    assert is_memorable("¡Hola!") is False


def test_fact_markers_make_short_text_memorable():
    # Below the word threshold, but an explicit fact marker wins.
    assert is_memorable("me llamo Andrés") is True
    assert is_memorable("recuerda esto") is True


def test_long_enough_substance_is_memorable():
    assert is_memorable("quiero agendar una reunión mañana temprano") is True


def test_short_smalltalk_below_threshold_is_not_memorable():
    assert is_memorable("todo bien", min_words=4) is False


def test_min_words_threshold_is_configurable():
    assert is_memorable("una dos tres", min_words=3) is True
    assert is_memorable("una dos tres", min_words=4) is False
