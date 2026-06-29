from infrastructure.config import Settings
from adapters.intent.gemini_function_calling_adapter import GeminiFunctionCallingAdapter
from adapters.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter
import inspect


def test_default_llm_model_is_deployable(monkeypatch):
    monkeypatch.setenv("KOKORO_ENDPOINT", "http://localhost")  # required field
    assert Settings().llm_model == "gemini-3.1-flash"


def test_adapter_default_model_matches_config():
    sig = inspect.signature(GeminiFunctionCallingAdapter.__init__)
    assert sig.parameters["model"].default == "gemini-3.1-flash"


def test_default_embedding_model_is_current():
    # Guards against the text-embedding-004 regression: that id 404s on
    # embedContent (v1beta), breaking the intent/skill cache lookup. Read the
    # field default directly (not Settings()) so the check pins the *code*
    # default regardless of any local .env override.
    assert Settings.model_fields["embedding_model"].default == "models/gemini-embedding-2"


def test_embedding_adapter_default_model_matches_config():
    sig = inspect.signature(GeminiEmbeddingAdapter.__init__)
    assert sig.parameters["model"].default == "models/gemini-embedding-2"
