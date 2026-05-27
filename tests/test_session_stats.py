"""Session stats endpoint."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SKIP_AUTH", "true")
os.environ.setdefault("DEV_USER_ID", "test_user_stats")

from app.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer dev"}


def test_session_stats_returns_shape(auth_headers):
    resp = client.get("/api/sessions/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "total",
        "draft",
        "processing",
        "ready",
        "error",
        "meeting",
        "interview",
        "with_output",
        "total_words",
    ):
        assert key in data
        assert isinstance(data[key], int)
