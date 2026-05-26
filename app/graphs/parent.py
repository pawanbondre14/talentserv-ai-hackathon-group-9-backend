"""Parent LangGraph: preprocess → budget → route → single | meeting | interview → validate."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graphs.interview.graph import get_interview_graph
from app.graphs.meeting.graph import get_meeting_graph
from app.graphs.nodes.budget import budget_check_node
from app.graphs.nodes.preprocess import preprocess_node
from app.graphs.nodes.route import route_after_strategy, route_strategy_node
from app.graphs.nodes.single_shot import single_shot_node
from app.graphs.nodes.validate import validate_output_node
from app.graphs.state import TranscriptState

_compiled_graph = None


def build_graph():
    graph = StateGraph(TranscriptState)
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("budget_check", budget_check_node)
    graph.add_node("route_strategy", route_strategy_node)
    graph.add_node("single_shot", single_shot_node)
    graph.add_node("meeting_graph", get_meeting_graph())
    graph.add_node("interview_graph", get_interview_graph())
    graph.add_node("validate_output", validate_output_node)

    graph.set_entry_point("preprocess")
    graph.add_edge("preprocess", "budget_check")
    graph.add_edge("budget_check", "route_strategy")
    graph.add_conditional_edges(
        "route_strategy",
        route_after_strategy,
        {
            "single_shot": "single_shot",
            "meeting_graph": "meeting_graph",
            "interview_graph": "interview_graph",
        },
    )
    graph.add_edge("single_shot", "validate_output")
    graph.add_edge("meeting_graph", "validate_output")
    graph.add_edge("interview_graph", "validate_output")
    graph.add_edge("validate_output", END)
    return graph.compile()


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def reset_compiled_graph() -> None:
    """Clear cached graph (tests / hot reload)."""
    global _compiled_graph
    _compiled_graph = None
