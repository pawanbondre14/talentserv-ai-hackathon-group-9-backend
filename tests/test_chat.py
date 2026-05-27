import os

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

os.environ["SKIP_AUTH"] = "true"
os.environ["DEV_USER_ID"] = "test_user_chat"
os.environ["LLM_MOCK"] = "true"
get_settings.cache_clear()

client = TestClient(app)

TRANSCRIPT = " ".join(["team meeting discussion action item owner deadline"] * 60)


def _create_ready_session():
    create = client.post(
        "/api/sessions",
        json={
            "title": "Chat test session",
            "mode": "meeting",
            "source": "paste",
            "transcript_text": TRANSCRIPT,
        },
    )
    assert create.status_code == 201
    session_id = create.json()["id"]
    proc = client.post(f"/api/sessions/{session_id}/process")
    assert proc.status_code == 200, proc.text
    return session_id


def test_chat_requires_ready_session():
    create = client.post(
        "/api/sessions",
        json={
            "title": "Draft only",
            "mode": "meeting",
            "source": "paste",
            "transcript_text": TRANSCRIPT,
        },
    )
    session_id = create.json()["id"]
    res = client.post(
        f"/api/sessions/{session_id}/chat",
        json={"content": "What were the action items?"},
    )
    assert res.status_code == 400


def test_chat_send_and_list():
    session_id = _create_ready_session()

    send = client.post(
        f"/api/sessions/{session_id}/chat",
        json={"content": "Summarize the main action items."},
    )
    assert send.status_code == 200, send.text
    body = send.json()
    assert body["user_message"]["role"] == "user"
    assert body["assistant_message"]["role"] == "assistant"
    assert len(body["assistant_message"]["content"]) > 10
    assert body["provider"] == "mock"

    listed = client.get(f"/api/sessions/{session_id}/chat")
    assert listed.status_code == 200
    assert listed.json()["total"] == 2

    cleared = client.delete(f"/api/sessions/{session_id}/chat")
    assert cleared.status_code == 200
    assert cleared.json()["deleted"] == 2
