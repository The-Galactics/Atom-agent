from infrastructure.container import _build_intent_use_case
from infrastructure.config import get_settings


class _SentinelChat:
    async def execute(self, input_dto):  # shape-compatible, never called here
        raise AssertionError("not called in wiring test")


def test_intent_use_case_receives_chat_use_case():
    get_settings.cache_clear()
    settings = get_settings()
    sentinel = _SentinelChat()
    use_case, status = _build_intent_use_case(settings, None, sentinel)
    assert use_case.chat_use_case is sentinel
