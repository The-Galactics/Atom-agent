from langgraph.graph import StateGraph, END
from application.agents.state import AgentState
from application.agents.nodes import GraphNodes


def build_graph(nodes: GraphNodes):
    # Build and compile the chat orchestration graph.
    # LangGraph state machine that orchestrates memory + LLM interaction.
    workflow = StateGraph(AgentState)

    # Nodes (retrieve semantic context -> generate response -> persist it).
    workflow.add_node("retrieve", nodes.retrieve_memory)
    workflow.add_node("generate", nodes.generate_response)
    workflow.add_node("store", nodes.store_memory)

    # Directed edges defining the execution flow.
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "store")
    workflow.add_edge("store", END)

    return workflow.compile()
