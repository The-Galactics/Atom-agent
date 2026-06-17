from langchain_google_genai import ChatGoogleGenerativeAI
from adapters.llm.content import extract_text
from domain.conversation.models import ChatMessage
from ports.llm_port import LLMPort


class GeminiAdapter(LLMPort):
    # LLM adapter backed by Google Gemini via LangChain.
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.7,
        )

    async def chat(self, messages: list[ChatMessage]) -> ChatMessage:
        # Translate internal messages into LangChain tuple format.
        langchain_messages = [
            ("system" if m.role == "system" else "human" if m.role == "user" else "ai", m.content)
            for m in messages
        ]
        response = await self.llm.ainvoke(langchain_messages)
        return ChatMessage(role="assistant", content=extract_text(response.content))
