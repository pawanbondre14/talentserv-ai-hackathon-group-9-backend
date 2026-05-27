"""LangGraph Send must include transcript context for specialist reviewers."""

from langgraph.types import Send

from app.graphs.interview.nodes import _review_worker_payload, map_review_dimensions


def test_review_worker_payload_includes_clean_text():
    state = {
        "session_id": "s1",
        "clean_text": "Interviewer: Hello\nCandidate: I built APIs.",
        "chunks": [{"chunk_id": "c_00", "text": "chunk"}],
        "merged_facts": {"classifications": []},
        "meta": {"word_count": 10},
    }
    payload = _review_worker_payload(state)
    assert payload["clean_text"].startswith("Interviewer")
    assert payload["chunks"]
    assert payload["merged_facts"] == {"classifications": []}


def test_map_review_dimensions_send_full_payload():
    state = {
        "session_id": "s1",
        "clean_text": "Full transcript body",
        "chunks": [],
        "merged_facts": {},
        "meta": {},
    }
    sends = map_review_dimensions(state)
    assert len(sends) == 3
    for s in sends:
        assert isinstance(s, Send)
        assert s.arg["clean_text"] == "Full transcript body"
