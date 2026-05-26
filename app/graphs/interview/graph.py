"""Interview subgraph compile (Phase C)."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graphs.interview.nodes import (
    aggregate_classifications_node,
    begin_interview_node,
    classify_chunk_node,
    extract_evidence_node,
    fairness_check_node,
    map_classify_chunks,
    map_review_dimensions,
    review_communication_node,
    review_culture_node,
    review_technical_node,
    synthesize_hiring_node,
)
from app.graphs.state import TranscriptState

_interview_graph = None


def build_interview_graph():
    graph = StateGraph(TranscriptState)
    graph.add_node("begin_interview", begin_interview_node)
    graph.add_node("classify_chunk", classify_chunk_node)
    graph.add_node("aggregate_classifications", aggregate_classifications_node)
    graph.add_node("review_technical", review_technical_node)
    graph.add_node("review_communication", review_communication_node)
    graph.add_node("review_culture", review_culture_node)
    graph.add_node("extract_evidence", extract_evidence_node)
    graph.add_node("synthesize_hiring", synthesize_hiring_node)
    graph.add_node("fairness_check", fairness_check_node)

    graph.set_entry_point("begin_interview")
    graph.add_conditional_edges("begin_interview", map_classify_chunks, ["classify_chunk"])
    graph.add_edge("classify_chunk", "aggregate_classifications")
    graph.add_conditional_edges(
        "aggregate_classifications", map_review_dimensions, ["review_technical", "review_communication", "review_culture"]
    )
    graph.add_edge("review_technical", "extract_evidence")
    graph.add_edge("review_communication", "extract_evidence")
    graph.add_edge("review_culture", "extract_evidence")
    graph.add_edge("extract_evidence", "synthesize_hiring")
    graph.add_edge("synthesize_hiring", "fairness_check")
    graph.add_edge("fairness_check", END)
    return graph.compile()


def get_interview_graph():
    global _interview_graph
    if _interview_graph is None:
        _interview_graph = build_interview_graph()
    return _interview_graph
