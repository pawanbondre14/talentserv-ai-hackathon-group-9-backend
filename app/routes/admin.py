import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.constants.permissions import RBAC_MANAGE
from app.database import get_db
from app.dependencies.authz import Principal, require_permission
from app.models import User
from app.schemas.rbac import AssignRoleRequest, PermissionOverrideRequest, UserRbacOut
from app.services.permissions import (
    assign_role_to_user,
    load_db_role_names,
    resolve_user_permissions,
    set_permission_override,
)
from app.config import Settings, get_settings

router = APIRouter()


def _get_target_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.post("/users/{user_id}/roles", response_model=UserRbacOut)
def assign_role(
    user_id: uuid.UUID,
    body: AssignRoleRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_permission(RBAC_MANAGE)),
    settings: Settings = Depends(get_settings),
):
    _ = principal
    user = _get_target_user(db, user_id)
    try:
        assign_role_to_user(db, user.id, body.role_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    roles, perms = resolve_user_permissions(db, user, None, settings)
    return UserRbacOut(
        user_id=user.id,
        roles=roles,
        permissions=sorted(perms),
    )


@router.post("/users/{user_id}/overrides", response_model=UserRbacOut)
def set_override(
    user_id: uuid.UUID,
    body: PermissionOverrideRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_permission(RBAC_MANAGE)),
    settings: Settings = Depends(get_settings),
):
    _ = principal
    user = _get_target_user(db, user_id)
    try:
        set_permission_override(db, user.id, body.permission_key, body.effect)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    roles, perms = resolve_user_permissions(db, user, None, settings)
    return UserRbacOut(
        user_id=user.id,
        roles=roles,
        permissions=sorted(perms),
    )


@router.get("/users/{user_id}/rbac", response_model=UserRbacOut)
def get_user_rbac(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_permission(RBAC_MANAGE)),
    settings: Settings = Depends(get_settings),
):
    _ = principal
    user = _get_target_user(db, user_id)
    roles = load_db_role_names(db, user.id)
    _, perms = resolve_user_permissions(db, user, None, settings)
    return UserRbacOut(
        user_id=user.id,
        roles=roles,
        permissions=sorted(perms),
    )
