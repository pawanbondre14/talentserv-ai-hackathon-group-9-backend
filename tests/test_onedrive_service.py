import os

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.teams_service import TeamsService

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


def test_browse_mock_root():
    res = client.get("/api/onedrive/browse", params={"folder_id": "root"})
    assert res.status_code == 200
    data = res.json()
    assert data["integration_mode"] == "mock"
    assert data["folder_id"] == "root"
    folders = [i for i in data["items"] if i["kind"] == "folder"]
    assert any(f["name"] == "Recordings" for f in folders)


def test_browse_mock_recordings():
    res = client.get("/api/onedrive/browse", params={"folder_id": "mock-recordings"})
    assert res.status_code == 200
    data = res.json()
    files = [i for i in data["items"] if i["kind"] == "file"]
    assert len(files) >= 3
    assert all(i["extension"] == ".vtt" for i in files)


def test_onedrive_import_mock_file():
    browse = client.get("/api/onedrive/browse", params={"folder_id": "mock-recordings"}).json()
    item = browse["items"][0]
    res = client.post(
        "/api/onedrive/import",
        json={
            "item_id": item["id"],
            "source": "mock",
            "mode": "meeting",
            "file_name": item["name"],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["word_count"] >= 10
    assert body["session"]["source"] == "mock"


def test_onedrive_recordings_alias():
    res = client.get("/api/onedrive/recordings")
    assert res.status_code == 200
    assert len(res.json()["items"]) >= 3


@pytest.mark.parametrize(
    "name,expected",
    [
        ("notes.txt", True),
        ("meeting.vtt", True),
        ("transcript-final.doc", True),
        ("photo.jpg", False),
        ("README.md", False),
    ],
)
def test_is_eligible_file(name: str, expected: bool):
    assert TeamsService._is_eligible_file(name) is expected


def test_parse_file_text_vtt():
    body = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello world"
    text = TeamsService.parse_file_text(body)
    assert "Hello world" in text


def test_parse_file_text_plain():
    body = "Plain transcript text here."
    assert TeamsService.parse_file_text(body) == "Plain transcript text here."


def test_onedrive_import_empty_transcript():
    """Empty transcript after parse maps to 422 via import error handler."""
    from app.errors import http_exception_from_import

    exc = http_exception_from_import(
        ValueError("No readable transcript text found in this file.")
    )
    assert exc.status_code == 422
