from langgraph.graph import StateGraph, END

from src.graph.state import LitGraphState
from src.graph.nodes import (
    supervisor,
    retriever,
    automation,
    safety,
    answerer,
    self_check,
    refuse,
)


def route_after_supervisor(state: LitGraphState) -> str:
    intent = state.get("intent")

    if intent == "refuse":
        return "refuse"

    if intent in ("qa", "guide"):
        return "retriever"

    return "refuse"


def route_after_retriever(state: LitGraphState) -> str:
    if state.get("error"):
        return "refuse"

    intent = state.get("intent")

    if intent == "guide":
        return "automation"

    if intent == "qa":
        return "safety"

    return "refuse"


def route_after_self_check(state: LitGraphState) -> str:
    if state.get("self_check_passed"):
        return "output"

    if state.get("self_check_attempts", 0) >= 2:
        return "refuse"

    if state.get("error"):
        return "refuse"

    return "retriever"


def build_graph():
    graph = StateGraph(LitGraphState)

    graph.add_node("supervisor", supervisor)
    graph.add_node("retriever", retriever)
    graph.add_node("automation", automation)
    graph.add_node("safety", safety)
    graph.add_node("answerer", answerer)
    graph.add_node("self_check", self_check)
    graph.add_node("refuse", refuse)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "retriever": "retriever",
            "refuse": "refuse",
        },
    )

    graph.add_conditional_edges(
        "retriever",
        route_after_retriever,
        {
            "automation": "automation",
            "safety": "safety",
            "refuse": "refuse",
        },
    )

    graph.add_edge("automation", "safety")
    graph.add_edge("safety", "answerer")
    graph.add_edge("answerer", "self_check")

    graph.add_conditional_edges(
        "self_check",
        route_after_self_check,
        {
            "output": "output",
            "retriever": "retriever",
            "refuse": "refuse",
        },
    )

    graph.add_edge("output", END)
    graph.add_edge("refuse", END)

    return graph.compile()