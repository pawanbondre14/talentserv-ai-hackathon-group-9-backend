"""RBAC permission keys and role-to-permission matrix."""

from __future__ import annotations

# --- Permission keys (resource:action) ---
SESSIONS_READ = "sessions:read"
SESSIONS_WRITE = "sessions:write"
SESSIONS_DELETE = "sessions:delete"
SESSIONS_CREATE = "sessions:create"
SESSIONS_READ_ALL = "sessions:read_all"
SESSIONS_WRITE_ALL = "sessions:write_all"
SESSIONS_PROCESS = "sessions:process"
INGEST_UPLOAD = "ingest:upload"
OUTPUT_EDIT = "output:edit"
CHAT_USE = "chat:use"
INTERVIEW_READ = "interview:read"
INTERVIEW_PROCESS = "interview:process"
INTEGRATIONS_MICROSOFT = "integrations:microsoft"
INTEGRATIONS_TEAMS = "integrations:teams"
INTEGRATIONS_ONEDRIVE = "integrations:onedrive"
RBAC_MANAGE = "rbac:manage"

ALL_PERMISSIONS: frozenset[str] = frozenset(
    {
        SESSIONS_READ,
        SESSIONS_WRITE,
        SESSIONS_DELETE,
        SESSIONS_CREATE,
        SESSIONS_READ_ALL,
        SESSIONS_WRITE_ALL,
        SESSIONS_PROCESS,
        INGEST_UPLOAD,
        OUTPUT_EDIT,
        CHAT_USE,
        INTERVIEW_READ,
        INTERVIEW_PROCESS,
        INTEGRATIONS_MICROSOFT,
        INTEGRATIONS_TEAMS,
        INTEGRATIONS_ONEDRIVE,
        RBAC_MANAGE,
    }
)

ROLE_ADMIN = "admin"
ROLE_RECRUITER = "recruiter"
ROLE_INTERVIEWER = "interviewer"
ROLE_VIEWER = "viewer"

DEFAULT_ROLE = ROLE_RECRUITER

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ROLE_ADMIN: ALL_PERMISSIONS,
    ROLE_RECRUITER: frozenset(
        {
            SESSIONS_READ,
            SESSIONS_WRITE,
            SESSIONS_DELETE,
            SESSIONS_CREATE,
            SESSIONS_PROCESS,
            INGEST_UPLOAD,
            OUTPUT_EDIT,
            CHAT_USE,
            INTERVIEW_READ,
            INTERVIEW_PROCESS,
            INTEGRATIONS_MICROSOFT,
            INTEGRATIONS_TEAMS,
            INTEGRATIONS_ONEDRIVE,
        }
    ),
    ROLE_INTERVIEWER: frozenset(
        {
            SESSIONS_READ,
            SESSIONS_PROCESS,
            OUTPUT_EDIT,
            CHAT_USE,
            INTERVIEW_READ,
            INTERVIEW_PROCESS,
        }
    ),
    ROLE_VIEWER: frozenset(
        {
            SESSIONS_READ,
            INTERVIEW_READ,
        }
    ),
}
