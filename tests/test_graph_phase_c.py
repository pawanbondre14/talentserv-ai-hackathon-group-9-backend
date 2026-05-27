"""Phase C LangGraph: interview multi-agent subgraph."""

import os
from pathlib import Path

import pytest

from app.config import Settings, get_settings
from app.graphs.context import reset_graph_settings, set_graph_settings
from app.graphs.interview.graph import build_interview_graph
from app.graphs.nodes.route import resolve_route
from app.graphs.parent import build_graph
from app.services.chunking import chunk_transcript
from app.services.graph_runner import run_analysis

os.environ.setdefault("SKIP_AUTH", "true")
os.environ.setdefault("DEV_USER_ID", "test_user_graph_c")
os.environ.setdefault("LLM_MOCK", "true")

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
SHORT_INTERVIEW = " ".join(["interview technical discussion"] * 60)
LONG_INTERVIEW = (SAMPLES / "interview_multi_agent_sample.txt").read_text(encoding="utf-8")


@pytest.fixture
def mock_settings():
    get_settings.cache_clear()
    settings = get_settings()
    settings.llm_mock = True
    settings.langgraph_enabled = True
    settings.multi_word_threshold = 800
    return settings


def test_resolve_route_interview_multi(mock_settings: Settings):
    token = set_graph_settings(mock_settings)
    try:
        chunks = chunk_transcript(LONG_INTERVIEW, max_words=800, overlap_words=100)
        state = {
            "mode": "interview",
            "strategy": "multi",
            "meta": {"word_count": len(LONG_INTERVIEW.split())},
            "chunks": chunks,
            "interview_options": {},
        }
        assert resolve_route(state) == "interview_graph"
        assert resolve_route({"mode": "interview", "strategy": "single", "meta": {}, "chunks": chunks}) == "single_shot"
        assert resolve_route(
            {
                "mode": "interview",
                "strategy": "multi",
                "meta": {},
                "chunks": chunks,
                "interview_options": {"panel_transcripts": ["extra panel text"]},
            }
        ) == "single_shot"
    finally:
        reset_graph_settings(token)


def test_interview_graph_multi_chunk_mock(mock_settings: Settings):
    graph = build_interview_graph()
    token = set_graph_settings(mock_settings)
    try:
        chunks = chunk_transcript(LONG_INTERVIEW[:8000], max_words=800, overlap_words=100)
        result = graph.invoke(
            {
                "session_id": "i1",
                "mode": "interview",
                "strategy": "multi",
                "clean_text": LONG_INTERVIEW[:8000],
                "chunks": chunks,
                "interview_options": {},
                "agent_trace": [],
            },
        )
    finally:
        reset_graph_settings(token)

    out = result.get("final_output") or {}
    assert out.get("rating") in ("Proceed", "Hold", "Reject")
    assert out.get("candidate_summary")
    nodes = [t["node"] for t in result.get("agent_trace", [])]
    assert nodes.count("classify_chunk") == len(chunks)
    assert "review_technical" in nodes
    assert "review_communication" in nodes
    assert "review_culture" in nodes
    assert "synthesize_hiring" in nodes
    assert "fairness_check" in nodes


def test_parent_graph_short_interview_single(mock_settings: Settings):
    graph = build_graph()
    token = set_graph_settings(mock_settings)
    try:
        result = graph.invoke(
            {
                "session_id": "i2",
                "mode": "interview",
                "strategy": "auto",
                "raw_transcript": SHORT_INTERVIEW,
                "interview_options": {},
                "agent_trace": [],
            },
        )
    finally:
        reset_graph_settings(token)

    nodes = [t["node"] for t in result.get("agent_trace", [])]
    assert "single_shot" in nodes
    assert "classify_chunk" not in nodes
    assert result["final_output"].get("rating") in ("Proceed", "Hold", "Reject")


def test_run_analysis_interview_multi(mock_settings: Settings):
    out = run_analysis(
        mock_settings,
        session_id="i3",
        mode="interview",
        transcript=LONG_INTERVIEW,
        strategy="multi",
        word_count=len(LONG_INTERVIEW.split()),
    )
    assert out.get("rating") in ("Proceed", "Hold", "Reject")
    assert "Multi-agent" in out.get("candidate_summary", "")
