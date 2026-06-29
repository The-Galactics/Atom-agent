import asyncio
from application.use_cases.chat import ChatUseCase
from application.dtos import ChatInputDTO


class _Graph:
    def __init__(self):
        self.seen_state = None

    async def ainvoke(self, state):
        self.seen_state = state
        return {**state, "response": type("M", (), {"content": "ok"})(),
                "messages": state["messages"] + []}


class _History:
    def get_history(self, sid): return []
    def add_message(self, sid, m): pass


def test_enable_web_search_flag_reaches_graph_state():
    g = _Graph()
    uc = ChatUseCase(g, _History())
    asyncio.run(uc.execute(ChatInputDTO(text="hi", session_id="s", enable_web_search=True)))
    assert g.seen_state["web_search"] is True


def test_default_web_search_is_false_in_graph_state():
    g = _Graph()
    uc = ChatUseCase(g, _History())
    asyncio.run(uc.execute(ChatInputDTO(text="hi", session_id="s")))
    assert g.seen_state["web_search"] is False
