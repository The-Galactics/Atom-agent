from adapters.llm.gemini_adapter import GeminiAdapter
from adapters.intent.gemini_function_calling_adapter import (
    GeminiFunctionCallingAdapter,
)
from infrastructure.config import get_settings


def test_chat_adapter_sets_max_output_tokens():
    a = GeminiAdapter(api_key="k", max_output_tokens=768)
    assert a.llm.max_output_tokens == 768


def test_intent_adapter_sets_max_output_tokens():
    a = GeminiFunctionCallingAdapter(api_key="k", max_output_tokens=256)
    # _llm is a RunnableBinding returned by bind_tools(); .bound is the base ChatGoogleGenerativeAI
    assert a._llm.bound.max_output_tokens == 256


def test_config_defaults():
    get_settings.cache_clear()
    s = get_settings()
    assert s.llm_max_output_tokens == 768
    assert s.llm_intent_max_output_tokens == 256
