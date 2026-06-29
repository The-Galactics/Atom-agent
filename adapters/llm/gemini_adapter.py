import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from adapters.llm.content import extract_text
from domain.conversation.models import ChatMessage
from infrastructure.observability.latency import timed
from ports.llm_port import LLMPort

logger = logging.getLogger("voice_module")

# Native Gemini grounding tool (Gemini 2.x and newer). Passed at invoke time so the model decides
# per-turn whether a web lookup is warranted (a greeting won't trigger a search).
_GOOGLE_SEARCH_TOOL = {"google_search": {}}


class GeminiAdapter(LLMPort):
    # LLM adapter backed by Google Gemini via LangChain.
    def __init__(self, api_key: str, model: str = "models/gemini-3.1-flash-lite",
                web_search: bool = False, max_output_tokens: int = 768):
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.7,
            max_output_tokens=max_output_tokens,
        )
        # Grounding requires a Gemini model with the google_search tool
        # (Gemini 2.x or newer) + a recent langchain-google-genai.
        self.web_search = web_search

    async def chat(self, messages: list[ChatMessage], web_search=None) -> ChatMessage:
        grounded = self.web_search if web_search is None else web_search
        # Translate internal messages into LangChain tuple format.
        langchain_messages = [
            ("system" if m.role == "system" else "human" if m.role == "user" else "ai", m.content)
            for m in messages
        ]
        response = await self._invoke(langchain_messages, grounded=grounded)
        return ChatMessage(role="assistant", content=extract_text(response.content))

    async def _invoke(self, langchain_messages, grounded=None):
        """Invoke the model, grounding with Google Search when enabled.

        Grounding is best-effort: if the installed model/library rejects the
        google_search tool we log once and fall back to an ungrounded call so a
        misconfiguration degrades the answer quality instead of breaking chat.
        The ``grounded`` flag overrides ``self.web_search`` when provided; pass
        ``None`` (the default) to use the construction-time setting.
        """
        effective = grounded if grounded is not None else self.web_search
        if effective:
            try:
                with timed("llm.chat"):
                    return await self.llm.ainvoke(
                        langchain_messages, tools=[_GOOGLE_SEARCH_TOOL]
                    )
            except Exception as exc:  # noqa: BLE001 - degrade, don't fail the turn
                logger.warning(
                    "web_search_grounding_failed falling_back_ungrounded error=%s", exc
                )
        with timed("llm.chat"):
            return await self.llm.ainvoke(langchain_messages)
