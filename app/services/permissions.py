"""Hybrid RBAC: JWT claims + DB roles + user overrides."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.constants.permissions import ALL_PERMISSIONS, DEFAULT_ROLE, ROLE_PERMISSIONS
from app.models import Permission, Role, User, UserPermissionOverride, UserRole


def _normalize_claim_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v).strip() for v in value if v and str(v).strip()]
    return []


def extract_token_roles(claims: dict[str, Any] | None, settings: Settings) -> list[str]:
    if not claims:
        return []
    roles = _normalize_claim_list(claims.get(settings.clerk_roles_claim))
    org_role = claims.get("org_role")
    if org_role and isinstance(org_role, str):
        roles.append(org_role.strip())
    return list(dict.fromkeys(roles))


def extract_token_permissions(claims: dict[str, Any] | None, settings: Settings) -> set[str]:
    if not claims:
        return set()
    perms = set(_normalize_claim_list(claims.get(settings.clerk_permissions_claim)))
    for role_name in extract_token_roles(claims, settings):
        perms.update(ROLE_PERMISSIONS.get(role_name, frozenset()))
    return perms


def _permissions_for_role_names(role_names: list[str]) -> set[str]:
    result: set[str] = set()
    for name in role_names:
        result.update(ROLE_PERMISSIONS.get(name, frozenset()))
    return result


def load_db_role_names(db: Session, user_id: uuid.UUID) -> list[str]:
    rows = (
        db.query(UserRole)
        .options(joinedload(UserRole.role))
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return [r.role.name for r in rows if r.role]


def load_db_permissions(db: Session, user_id: uuid.UUID) -> set[str]:
    rows = (
        db.query(UserRole)
        .options(joinedload(UserRole.role).joinedload(Role.permissions))
        .filter(UserRole.user_id == user_id)
        .all()
    )
    keys: set[str] = set()
    for ur in rows:
        if ur.role:
            for perm in ur.role.permissions:
                keys.add(perm.key)
    return keys


def load_db_overrides(db: Session, user_id: uuid.UUID) -> tuple[set[str], set[str]]:
    rows = (
        db.query(UserPermissionOverride)
        .options(joinedload(UserPermissionOverride.permission))
        .filter(UserPermissionOverride.user_id == user_id)
        .all()
    )
    grants: set[str] = set()
    denies: set[str] = set()
    for row in rows:
        if not row.permission:
            continue
        if row.effect == "grant":
            grants.add(row.permission.key)
        elif row.effect == "deny":
            denies.add(row.permission.key)
    return grants, denies


def compute_effective_permissions(
    *,
    db_role_names: list[str],
    db_permissions: set[str],
    token_permissions: set[str],
    token_role_names: list[str],
    grants: set[str],
    denies: set[str],
    skip_auth_all: bool = False,
) -> set[str]:
    if skip_auth_all:
        return set(ALL_PERMISSIONS)

    role_perms = _permissions_for_role_names(db_role_names)
    role_perms.update(_permissions_for_role_names(token_role_names))

    effective = set()
    effective.update(db_permissions)
    effective.update(role_perms)
    effective.update(token_permissions)
    effective.update(grants)
    effective -= denies
    return effective


def resolve_user_permissions(
    db: Session,
    user: User,
    claims: dict[str, Any] | None,
    settings: Settings,
    *,
    skip_auth_all: bool = False,
) -> tuple[list[str], set[str]]:
    try:
        db_roles = load_db_role_names(db, user.id)
        db_perms = load_db_permissions(db, user.id)
        grants, denies = load_db_overrides(db, user.id)
    except SQLAlchemyError:
        db.rollback()
        db_roles = []
        db_perms = set()
        grants, denies = set(), set()
    token_roles = extract_token_roles(claims, settings)
    token_perms = extract_token_permissions(claims, settings)

    all_roles = list(dict.fromkeys(db_roles + token_roles))
    effective = compute_effective_permissions(
        db_role_names=db_roles,
        db_permissions=db_perms,
        token_permissions=token_perms,
        token_role_names=token_roles,
        grants=grants,
        denies=denies,
        skip_auth_all=skip_auth_all,
    )
    return all_roles, effective


def ensure_default_role(db: Session, user: User, default_role: str = DEFAULT_ROLE) -> None:
    """Assign default role to new users if they have no roles."""
    try:
        existing = db.query(UserRole).filter(UserRole.user_id == user.id).first()
        if existing:
            return
        role = db.query(Role).filter(Role.name == default_role).first()
        if not role:
            return
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
    except SQLAlchemyError:
        db.rollback()


def assign_role_to_user(db: Session, user_id: uuid.UUID, role_name: str) -> None:
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise ValueError(f"Unknown role: {role_name}")
    existing = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role_id == role.id)
        .first()
    )
    if not existing:
        db.add(UserRole(user_id=user_id, role_id=role.id))
        db.commit()


def set_permission_override(
    db: Session, user_id: uuid.UUID, permission_key: str, effect: str
) -> None:
    perm = db.query(Permission).filter(Permission.key == permission_key).first()
    if not perm:
        raise ValueError(f"Unknown permission: {permission_key}")
    if effect not in ("grant", "deny"):
        raise ValueError("effect must be grant or deny")

    row = (
        db.query(UserPermissionOverride)
        .filter(
            UserPermissionOverride.user_id == user_id,
            UserPermissionOverride.permission_id == perm.id,
        )
        .first()
    )
    if row:
        row.effect = effect
    else:
        db.add(
            UserPermissionOverride(
                user_id=user_id, permission_id=perm.id, effect=effect
            )
        )
    db.commit()


def has_permission(permissions: set[str], required: str) -> bool:
    return required in permissions
