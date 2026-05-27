import os

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.interview_redact import redact_pii
from app.services.scorecards import get_scorecard, list_scorecards

os.environ["SKIP_AUTH"] = "true"
os.environ["DEV_USER_ID"] = "test_user_phase5"
os.environ["LLM_MOCK"] = "true"
get_settings.cache_clear()

client = TestClient(app)

LONG_TRANSCRIPT = " ".join(["interview discussion word"] * 60)


def test_redact_pii():
    text = "Contact jane.doe@example.com or call 555-123-4567. LinkedIn: linkedin.com/in/janedoe"
    out = redact_pii(text)
    assert "[EMAIL]" in out
    assert "[PHONE]" in out
    assert "[PROFILE]" in out
    assert "jane.doe@example.com" not in out


def test_scorecards_load():
    cards = list_scorecards()
    assert len(cards) >= 3
    backend = get_scorecard("backend")
    assert backend is not None
    assert any(c["id"] == "api_design" for c in backend["criteria"])


def test_interview_process_with_scorecard_and_jd():
    create = client.post(
        "/api/sessions",
        json={
            "title": "Backend interview",
            "mode": "interview",
            "source": "paste",
            "transcript_text": LONG_TRANSCRIPT,
        },
    )
    assert create.status_code == 201
    session_id = create.json()["id"]

    proc = client.post(
        f"/api/sessions/{session_id}/process",
        json={
            "interview_options": {
                "jd_text": "Python backend engineer with REST API experience.",
                "scorecard_id": "backend",
                "blind_mode": True,
                "candidate_name": "Jane Doe",
            }
        },
    )
    assert proc.status_code == 200, proc.text
    body = proc.json()
    out = body["output"]["ai_json"]
    assert out["rating"] in ("Proceed", "Hold", "Reject")
    assert "qa_pairs" in out
    assert len(out["qa_pairs"]) >= 1
    assert "scorecard_scores" in out
    assert "jd_analysis" in out
    assert out["jd_analysis"]["overall_fit_score"] >= 1

    full = client.get(f"/api/sessions/{session_id}/full")
    assert full.status_code == 200
    meta = full.json().get("interview_meta")
    assert meta is not None
    assert meta["scorecard_id"] == "backend"
    assert meta["blind_mode"] is True


def test_scorecards_endpoint():
    res = client.get("/api/interview/scorecards")
    assert res.status_code == 200
    assert any(c["id"] == "frontend" for c in res.json())
