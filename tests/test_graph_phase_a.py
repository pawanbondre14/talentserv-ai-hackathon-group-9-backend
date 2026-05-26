"""Phase A LangGraph: minimal graph + feature flag."""

import os

import pytest

from app.config import Settings, get_settings
from app.graphs.parent import build_graph
from app.services.graph_runner import run_analysis

os.environ.setdefault("SKIP_AUTH", "true")
os.environ.setdefault("DEV_USER_ID", "test_user_graph_a")
os.environ.setdefault("LLM_MOCK", "true")

MEETING_TEXT = " ".join(["team discussed roadmap and deadlines"] * 12)
INTERVIEW_TEXT = " ".join(["interview technical discussion"] * 60)


@pytest.fixture
def mock_settings():
    get_settings.cache_clear()
    settings = get_settings()
    settings.llm_mock = True
    settings.langgraph_enabled = True
    return settings


def test_graph_nodes_meeting_mock(mock_settings: Settings):
    graph = build_graph()
    from app.graphs.context import reset_graph_settings, set_graph_settings

    token = set_graph_settings(mock_settings)
    try:
        result = graph.invoke(
            {
                "session_id": "test-session",
                "mode": "meeting",
                "strategy": "single",
                "raw_transcript": MEETING_TEXT,
                "interview_options": {},
                "agent_trace": [],
                "meta": {"word_count": 60, "truncated": False},
            },
            {"configurable": {"settings": mock_settings}},
        )
    finally:
        reset_graph_settings(token)
    assert result.get("final_output")
    assert result["final_output"].get("executive_summary")
    assert not result.get("validation_errors")
    nodes = [t["node"] for t in result.get("agent_trace", [])]
    assert "preprocess" in nodes
    assert "single_shot" in nodes
    assert "validate_output" in nodes


def test_graph_nodes_interview_mock(mock_settings: Settings):
    graph = build_graph()
    from app.graphs.context import reset_graph_settings, set_graph_settings

    token = set_graph_settings(mock_settings)
    try:
        result = graph.invoke(
            {
                "session_id": "test-session",
                "mode": "interview",
                "strategy": "auto",
                "raw_transcript": INTERVIEW_TEXT,
                "interview_options": {},
                "agent_trace": [],
            },
            {"configurable": {"settings": mock_settings}},
        )
    finally:
        reset_graph_settings(token)
    out = result["final_output"]
    assert out.get("rating") in ("Proceed", "Hold", "Reject")
    assert out.get("candidate_summary")


def test_run_analysis_legacy_fallback():
    get_settings.cache_clear()
    settings = get_settings()
    settings.llm_mock = True
    settings.langgraph_enabled = False
    out = run_analysis(
        settings,
        session_id="s1",
        mode="meeting",
        transcript=MEETING_TEXT,
        word_count=50,
    )
    assert out.get("executive_summary")


def test_run_analysis_langgraph_path(mock_settings: Settings):
    out = run_analysis(
        mock_settings,
        session_id="s2",
        mode="meeting",
        transcript=MEETING_TEXT,
        strategy="single",
        word_count=50,
    )
    assert out.get("action_items") is not None
