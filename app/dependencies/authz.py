"""Authorization dependencies for FastAPI routes."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user, get_or_create_db_user
from app.config import Settings, get_settings
from app.database import get_db
from app.errors import raise_forbidden
from app.models import SessionRecord, User
from app.services.permissions import ensure_default_role, has_permission, resolve_user_permissions


class Principal:
    """Authenticated user with resolved RBAC context."""

    def __init__(
        self,
        *,
        auth_user: AuthUser,
        db_user: User,
        roles: list[str],
        permissions: set[str],
    ):
        self.auth_user = auth_user
        self.db_user = db_user
        self.user_id = db_user.id
        self.clerk_user_id = auth_user.clerk_user_id
        self.email = auth_user.email
        self.roles = roles
        self.permissions = permissions

    def can(self, permission: str) -> bool:
        return has_permission(self.permissions, permission)


async def get_current_principal(
    auth: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Principal:
    user = get_or_create_db_user(db, auth)
    ensure_default_role(db, user, default_role=settings.default_user_role)
    roles, perms = resolve_user_permissions(
        db,
        user,
        auth.jwt_claims,
        settings,
        skip_auth_all=settings.skip_auth,
    )
    return Principal(
        auth_user=auth,
        db_user=user,
        roles=roles,
        permissions=perms,
    )


def require_permission(permission: str) -> Callable[..., Principal]:
    async def _check(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.can(permission):
            raise_forbidden(permission)
        return principal

    return _check


def require_any_permission(*permissions: str) -> Callable[..., Principal]:
    async def _check(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not any(principal.can(p) for p in permissions):
            raise_forbidden(permissions[0] if permissions else "unknown")
        return principal

    return _check


def get_session_for_principal(
    db: Session,
    principal: Principal,
    session_id: uuid.UUID,
    *,
    read: bool = True,
) -> SessionRecord:
    """Return session if principal owns it or has elevated read/write-all."""
    from app.constants.permissions import SESSIONS_READ_ALL, SESSIONS_WRITE_ALL

    elevated = SESSIONS_READ_ALL if read else SESSIONS_WRITE_ALL
    if principal.can(elevated):
        session = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
    else:
        session = (
            db.query(SessionRecord)
            .filter(
                SessionRecord.id == session_id,
                SessionRecord.user_id == principal.user_id,
            )
            .first()
        )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session
