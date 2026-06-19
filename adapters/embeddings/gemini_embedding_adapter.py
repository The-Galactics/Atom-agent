from langchain_google_genai import GoogleGenerativeAIEmbeddings
from ports.embedding_port import EmbeddingPort


class GeminiEmbeddingAdapter(EmbeddingPort):
    # Embedding adapter backed by Google Generative AI embeddings.
    def __init__(self, api_key: str, model: str = "models/text-embedding-004"):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=model,
            google_api_key=api_key
        )

    async def embed_text(self, text: str) -> list[float]:
        # Async embedding call keeps the event loop unblocked during the
        # network round-trip (invoked from async QdrantAdapter store/search).
        return await self.embeddings.aembed_query(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self.embeddings.aembed_documents(texts)
