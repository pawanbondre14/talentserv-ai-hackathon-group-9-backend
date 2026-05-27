from app.services.search_index import extract_snippet
from app.models import SessionRecord, Output


def test_extract_snippet_highlights_query():
    session = SessionRecord(
        title="Test",
        transcript_text="We decided to ship the MVP by June with the backend team.",
    )
    snippet = extract_snippet(session, None, query="MVP")
    assert "MVP" in snippet or "mvp" in snippet.lower()


def test_extract_snippet_from_output_summary():
    session = SessionRecord(title="Interview", transcript_text="")
    output = Output(
        edited_json={
            "candidate_summary": "Strong Python skills demonstrated throughout.",
        }
    )
    snippet = extract_snippet(session, output, query=None)
    assert "Python" in snippet
