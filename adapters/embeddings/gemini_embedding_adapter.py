from langchain_google_genai import GoogleGenerativeAIEmbeddings
from ports.embedding_port import EmbeddingPort


class GeminiEmbeddingAdapter(EmbeddingPort):
    # Embedding adapter backed by Google Generative AI embeddings.
    def __init__(self, api_key: str, model: str = "models/text-embedding-004"):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=model,
            google_api_key=api_key
        )

    def embed_text(self, text: str) -> list[float]:
        return self.embeddings.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embeddings.embed_documents(texts)
