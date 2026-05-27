from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

get_settings.cache_clear()


def test_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "MeetingFeed" in response.json()["app"]


def test_health():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
