import os
import uuid

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

os.environ["SKIP_AUTH"] = "true"
os.environ["DEV_USER_ID"] = "test_delete_user"
get_settings.cache_clear()

client = TestClient(app)


def test_delete_session_with_output():
    create = client.post(
        "/api/sessions",
        json={
            "title": "To delete",
            "mode": "meeting",
            "transcript_text": "word " * 60,
        },
    )
    assert create.status_code == 201
    session_id = create.json()["id"]

    process = client.post(f"/api/sessions/{session_id}/process")
    assert process.status_code == 200, process.text

    delete = client.delete(f"/api/sessions/{session_id}")
    assert delete.status_code == 204, delete.text

    get = client.get(f"/api/sessions/{session_id}")
    assert get.status_code == 404


def test_delete_nonexistent_returns_404():
    fake = str(uuid.uuid4())
    res = client.delete(f"/api/sessions/{fake}")
    assert res.status_code == 404
