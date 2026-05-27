"""Phase B LangGraph: meeting map-reduce subgraph."""

import os
from pathlib import Path

import pytest

from app.config import Settings, get_settings
from app.graphs.context import reset_graph_settings, set_graph_settings
from app.graphs.meeting.graph import build_meeting_graph
from app.graphs.nodes.route import resolve_route
from app.graphs.parent import build_graph
from app.services.chunking import chunk_transcript
from app.services.graph_runner import run_analysis

os.environ.setdefault("SKIP_AUTH", "true")
os.environ.setdefault("DEV_USER_ID", "test_user_graph_b")
os.environ.setdefault("LLM_MOCK", "true")

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
SHORT_MEETING = " ".join(["team discussed roadmap and deadlines"] * 12)
LONG_MEETING = (SAMPLES / "meeting_multi_agent_sample.txt").read_text(encoding="utf-8")


@pytest.fixture
def mock_settings():
    get_settings.cache_clear()
    settings = get_settings()
    settings.llm_mock = True
    settings.langgraph_enabled = True
    settings.multi_word_threshold = 800
    settings.chunk_max_words = 800
    settings.chunk_overlap_words = 100
    return settings


def test_chunk_transcript_splits_long_text():
    text = "word " * 2500
    chunks = chunk_transcript(text.strip(), max_words=800, overlap_words=100)
    assert len(chunks) >= 3
    assert chunks[0]["chunk_id"] == "c_00"
    assert all(c.get("text") for c in chunks)


def test_resolve_route_auto_long_meeting(mock_settings: Settings):
    token = set_graph_settings(mock_settings)
    try:
        chunks = chunk_transcript(LONG_MEETING, max_words=800, overlap_words=100)
        state = {
            "mode": "meeting",
            "strategy": "auto",
            "meta": {"word_count": len(LONG_MEETING.split())},
            "chunks": chunks,
        }
        assert resolve_route(state) == "meeting_graph"
        assert resolve_route({"mode": "meeting", "strategy": "single", "meta": {}, "chunks": chunks}) == "single_shot"
        assert resolve_route({"mode": "interview", "strategy": "multi", "meta": {}, "chunks": chunks}) == "interview_graph"
    finally:
        reset_graph_settings(token)


def test_meeting_graph_multi_chunk_mock(mock_settings: Settings):
    graph = build_meeting_graph()
    token = set_graph_settings(mock_settings)
    try:
        chunks = chunk_transcript(LONG_MEETING[:6000], max_words=800, overlap_words=100)
        result = graph.invoke(
            {
                "session_id": "m1",
                "mode": "meeting",
                "strategy": "multi",
                "clean_text": LONG_MEETING[:6000],
                "chunks": chunks,
                "agent_trace": [],
            },
        )
    finally:
        reset_graph_settings(token)

    assert result.get("final_output", {}).get("executive_summary")
    nodes = [t["node"] for t in result.get("agent_trace", [])]
    assert nodes.count("summarize_chunk") == len(chunks)
    assert "synthesize_minutes" in nodes


def test_parent_graph_short_meeting_single_path(mock_settings: Settings):
    graph = build_graph()
    token = set_graph_settings(mock_settings)
    try:
        result = graph.invoke(
            {
                "session_id": "s1",
                "mode": "meeting",
                "strategy": "auto",
                "raw_transcript": SHORT_MEETING,
                "agent_trace": [],
            },
        )
    finally:
        reset_graph_settings(token)

    nodes = [t["node"] for t in result.get("agent_trace", [])]
    assert "single_shot" in nodes
    assert "summarize_chunk" not in nodes
    assert result["final_output"].get("executive_summary")


def test_run_analysis_meeting_multi_strategy(mock_settings: Settings):
    out = run_analysis(
        mock_settings,
        session_id="m2",
        mode="meeting",
        transcript=LONG_MEETING,
        strategy="multi",
        word_count=len(LONG_MEETING.split()),
    )
    assert out.get("executive_summary")
    assert "Multi-agent" in out.get("executive_summary", "") or out.get("action_items")
