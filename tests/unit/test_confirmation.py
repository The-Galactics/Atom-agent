from domain.intent.confirmation import confirmation_prompt
from domain.intent.models import ActionType


def test_make_call_names_the_target():
    assert confirmation_prompt(ActionType.MAKE_CALL, {"target": "María"}) == "¿Confirmas que llame a María?"


def test_send_message_names_the_recipient():
    prompt = confirmation_prompt(ActionType.SEND_MESSAGE, {"recipient": "Juan", "body": "hola"})
    assert prompt == "¿Confirmas que envíe el mensaje a Juan?"


def test_tap_element_quotes_the_text():
    assert confirmation_prompt(ActionType.TAP_ELEMENT, {"text": "Pagar"}) == "¿Confirmas que pulse 'Pagar'?"


def test_missing_params_use_generic_fallback():
    assert confirmation_prompt(ActionType.MAKE_CALL, {}) == "¿Confirmas que haga la llamada?"
    assert confirmation_prompt(ActionType.OPEN_APP, {"app_name": "x"}) == "¿Confirmas esta acción?"
