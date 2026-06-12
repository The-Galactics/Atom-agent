from sentence_transformers import SentenceTransformer
from ports.embedding_port import EmbeddingPort


class BGEM3Adapter(EmbeddingPort):
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts).tolist()
