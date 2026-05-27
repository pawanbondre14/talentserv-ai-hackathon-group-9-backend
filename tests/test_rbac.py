"""RBAC API tests (SKIP_AUTH grants admin-equivalent permissions)."""

import os

from fastapi.testclient import TestClient

from app.auth import AuthUser, get_or_create_db_user
from app.config import get_settings
from app.database import SessionLocal
from app.dependencies.authz import Principal, get_current_principal
from app.main import app

os.environ["SKIP_AUTH"] = "true"
os.environ["DEV_USER_ID"] = "test_rbac_user"
get_settings.cache_clear()

client = TestClient(app)


def test_me_returns_permissions():
    response = client.get("/api/me")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "user" in data
    assert "roles" in data
    assert "permissions" in data
    assert isinstance(data["permissions"], list)
    assert len(data["permissions"]) > 0
    assert "sessions:read" in data["permissions"]


def test_forbidden_without_permission():
    """Viewer permissions lack sessions:create — expect 403 on create."""
    db = SessionLocal()
    try:
        auth = AuthUser(clerk_user_id="test_rbac_viewer", email="viewer@test.com")
        user = get_or_create_db_user(db, auth)

        async def viewer_principal():
            return Principal(
                auth_user=auth,
                db_user=user,
                roles=["viewer"],
                permissions={"sessions:read", "interview:read"},
            )

        app.dependency_overrides[get_current_principal] = viewer_principal
        response = client.post(
            "/api/sessions",
            json={
                "title": "Blocked",
                "mode": "meeting",
                "source": "paste",
                "transcript_text": "Test transcript with enough words for validation here.",
            },
        )
        assert response.status_code == 403
        detail = response.json()["detail"]
        assert detail["code"] == "forbidden"
        assert detail["required_permission"] == "sessions:create"
    finally:
        app.dependency_overrides.clear()
        db.close()
