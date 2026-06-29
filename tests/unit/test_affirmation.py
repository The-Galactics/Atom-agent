from domain.intent.affirmation import classify_affirmation


def test_affirmative_spanish_and_english():
    for text in ["sí", "si", "claro", "dale", "vale", "ok", "hazlo", "confirmo",
                 "confirmar", "confirma", "yes", "yeah", "sure", "go ahead",
                 "sí por favor"]:
        assert classify_affirmation(text) == "yes", text


def test_negative_spanish_and_english():
    for text in ["no", "cancela", "cancelo", "cancelar", "para", "detente",
                 "mejor no", "no gracias", "nope", "cancel", "stop", "no lo hagas"]:
        assert classify_affirmation(text) == "no", text


def test_colloquial_colombian_variants():
    for text in ["simón", "sisas", "de una", "obvio", "listo", "por supuesto",
                 "claro que sí", "hágale pues"]:
        assert classify_affirmation(text) == "yes", text
    for text in ["qué va", "para nada", "claro que no", "ni loco", "nada que ver"]:
        assert classify_affirmation(text) == "no", text


def test_unclear_includes_dont_know_phrases():
    # "no sé" contains the token "no" but must NOT be read as a rejection.
    for text in ["no sé", "no se", "ehh", "tal vez", "quizás", "ni idea",
                 "not sure", "i don't know", "maybe", ""]:
        assert classify_affirmation(text) == "unclear", text


def test_mixed_yes_and_no_is_unclear():
    assert classify_affirmation("sí pero no") == "unclear"


def test_accents_and_case_insensitive():
    assert classify_affirmation("SÍ") == "yes"
    assert classify_affirmation("Sí, claro.") == "yes"
    assert classify_affirmation("NO.") == "no"
