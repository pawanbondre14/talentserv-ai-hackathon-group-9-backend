"""Meeting subgraph compile (map-reduce)."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graphs.meeting.nodes import (
    begin_meeting_node,
    link_entities_node,
    map_summarize_chunks,
    merge_actions_node,
    summarize_chunk_node,
    synthesize_minutes_node,
)
from app.graphs.state import TranscriptState


def build_meeting_graph():
    graph = StateGraph(TranscriptState)
    graph.add_node("begin_meeting", begin_meeting_node)
    graph.add_node("summarize_chunk", summarize_chunk_node)
    graph.add_node("link_entities", link_entities_node)
    graph.add_node("merge_actions", merge_actions_node)
    graph.add_node("synthesize_minutes", synthesize_minutes_node)

    graph.set_entry_point("begin_meeting")
    graph.add_conditional_edges("begin_meeting", map_summarize_chunks, ["summarize_chunk"])
    graph.add_edge("summarize_chunk", "link_entities")
    graph.add_edge("link_entities", "merge_actions")
    graph.add_edge("merge_actions", "synthesize_minutes")
    graph.add_edge("synthesize_minutes", END)
    return graph.compile()


_meeting_graph = None


def get_meeting_graph():
    global _meeting_graph
    if _meeting_graph is None:
        _meeting_graph = build_meeting_graph()
    return _meeting_graph
