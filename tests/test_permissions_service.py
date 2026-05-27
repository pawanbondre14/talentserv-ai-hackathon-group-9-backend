"""Unit tests for hybrid permission resolution."""

from app.constants.permissions import (
    CHAT_USE,
    ROLE_ADMIN,
    ROLE_RECRUITER,
    ROLE_VIEWER,
    SESSIONS_READ,
)
from app.services.permissions import compute_effective_permissions


def test_skip_auth_grants_all():
    perms = compute_effective_permissions(
        db_role_names=[],
        db_permissions=set(),
        token_permissions=set(),
        token_role_names=[],
        grants=set(),
        denies=set(),
        skip_auth_all=True,
    )
    assert CHAT_USE in perms
    assert SESSIONS_READ in perms


def test_role_derived_permissions():
    perms = compute_effective_permissions(
        db_role_names=[ROLE_RECRUITER],
        db_permissions=set(),
        token_permissions=set(),
        token_role_names=[],
        grants=set(),
        denies=set(),
    )
    assert SESSIONS_READ in perms
    assert CHAT_USE in perms


def test_token_roles_union():
    perms = compute_effective_permissions(
        db_role_names=[],
        db_permissions=set(),
        token_permissions=set(),
        token_role_names=[ROLE_ADMIN],
        grants=set(),
        denies=set(),
    )
    assert CHAT_USE in perms


def test_deny_override_wins():
    perms = compute_effective_permissions(
        db_role_names=[ROLE_RECRUITER],
        db_permissions=set(),
        token_permissions=set(),
        token_role_names=[],
        grants=set(),
        denies={CHAT_USE},
    )
    assert SESSIONS_READ in perms
    assert CHAT_USE not in perms


def test_grant_override_adds_permission():
    perms = compute_effective_permissions(
        db_role_names=[ROLE_VIEWER],
        db_permissions=set(),
        token_permissions=set(),
        token_role_names=[],
        grants={CHAT_USE},
        denies=set(),
    )
    assert CHAT_USE in perms
    assert SESSIONS_READ in perms
