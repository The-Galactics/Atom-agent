from __future__ import annotations

from ports.embedding_port import EmbeddingPort


class BGEM3Adapter(EmbeddingPort):
    """Embedding adapter backed by a SentenceTransformer model.

    The model (BAAI/bge-m3, ~2GB) is loaded lazily on first use so that
    constructing the adapter never blocks startup or forces a download when
    the model is not cached. If the model cannot be loaded, the underlying
    error propagates to the caller, which is expected to handle it at the
    node/use-case boundary and degrade gracefully (memory-disabled).
    """

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            # Imported lazily so a missing/heavy dependency does not break
            # module import or container construction.
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        return self._ensure_model().encode(text).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._ensure_model().encode(texts).tolist()
