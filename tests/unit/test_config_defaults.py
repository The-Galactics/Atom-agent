from infrastructure.config import Settings
from adapters.intent.gemini_function_calling_adapter import GeminiFunctionCallingAdapter
import inspect


def test_default_llm_model_is_deployable(monkeypatch):
    monkeypatch.setenv("KOKORO_ENDPOINT", "http://localhost")  # required field
    assert Settings().llm_model == "gemini-3.1-flash"


def test_adapter_default_model_matches_config():
    sig = inspect.signature(GeminiFunctionCallingAdapter.__init__)
    assert sig.parameters["model"].default == "gemini-3.1-flash"
