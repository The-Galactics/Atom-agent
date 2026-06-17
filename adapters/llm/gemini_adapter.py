from langchain_google_genai import ChatGoogleGenerativeAI
from domain.conversation.models import ChatMessage
from ports.llm_port import LLMPort


def _extract_text(content) -> str:
    """Normalize a LangChain message content into plain text.

    Gemini 1.x/2.x return a plain ``str``; Gemini 3.x return a list of content
    blocks (``{"type": "text", "text": ..., "extras": {...}}``) that may include
    non-display blocks (reasoning / thought signatures). We keep only the visible
    text so the client never sees the raw block structure.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") in (None, "text"):
                text = block.get("text")
                if text:
                    parts.append(text)
        joined = "".join(parts).strip()
        return joined if joined else str(content)
    return str(content)


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
        return ChatMessage(role="assistant", content=_extract_text(response.content))
