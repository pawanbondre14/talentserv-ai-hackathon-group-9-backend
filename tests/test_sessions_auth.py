import os

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

os.environ["SKIP_AUTH"] = "true"
os.environ["DEV_USER_ID"] = "test_user_phase1"
get_settings.cache_clear()

client = TestClient(app)


def test_create_and_list_session():
    create = client.post(
        "/api/sessions",
        json={
            "title": "Sprint planning",
            "mode": "meeting",
            "source": "paste",
            "transcript_text": "We discussed the roadmap and assigned tasks to the team.",
        },
    )
    assert create.status_code == 201, create.text
    session_id = create.json()["id"]

    listed = client.get("/api/sessions")
    assert listed.status_code == 200
    data = listed.json()
    assert data["total"] >= 1
    assert any(item["id"] == session_id for item in data["items"])

    detail = client.get(f"/api/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Sprint planning"
