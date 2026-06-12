from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from domain.conversation.models import ChatMessage
from ports.llm_port import LLMPort


class NvidiaGemmaAdapter(LLMPort):
    def __init__(self, api_key: str, model: str):
        self.client = ChatNVIDIA(
            model=model,
            nvidia_api_key=api_key,
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatMessage:
        langchain_messages = []
        for msg in messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))

        response = await self.client.ainvoke(
            langchain_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return ChatMessage(role="assistant", content=response.content)
