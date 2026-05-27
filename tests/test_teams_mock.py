import os

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

os.environ["SKIP_AUTH"] = "true"
os.environ["TEAMS_INTEGRATION_MODE"] = "mock"
get_settings.cache_clear()

client = TestClient(app)


def test_list_mock_transcripts():
    res = client.get("/api/teams/transcripts")
    assert res.status_code == 200
    data = res.json()
    assert data["integration_mode"] == "mock"
    assert len(data["items"]) >= 3


def test_import_mock_transcript():
    listed = client.get("/api/teams/transcripts").json()
    meeting_id = listed["items"][0]["id"]
    res = client.post(
        "/api/teams/import",
        json={
            "meeting_id": meeting_id,
            "source": "mock",
            "mode": "meeting",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["word_count"] >= 10
    assert res.json()["session"]["source"] == "mock"
