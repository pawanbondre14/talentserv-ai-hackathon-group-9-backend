import httpx
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.auth import AuthUser, get_or_create_db_user

DB_UNAVAILABLE_DETAIL = (
    "Database unavailable. In .env use the Supabase Transaction pooler URI "
    "(host contains pooler.supabase.com, port 6543)."
)

AI_PROCESSING_FAILED = "AI processing failed. Try again in a moment."
GRAPH_UNAVAILABLE = "Could not reach Microsoft OneDrive. Try again later."


def get_db_user_or_503(db, auth: AuthUser):
    try:
        return get_or_create_db_user(db, auth)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from exc


def http_exception_from_import(exc: Exception) -> HTTPException:
    """Map OneDrive / Teams import errors to user-safe HTTP responses."""
    if isinstance(exc, HTTPException):
        return exc

    if isinstance(exc, ValueError):
        return _http_from_value_error(str(exc))

    if isinstance(exc, httpx.HTTPStatusError):
        return _http_from_graph_status(exc.response.status_code)

    if isinstance(exc, httpx.RequestError):
        return HTTPException(status_code=502, detail=GRAPH_UNAVAILABLE)

    return HTTPException(
        status_code=502,
        detail="Could not import file from OneDrive. Try again later.",
    )


def _http_from_value_error(message: str) -> HTTPException:
    lower = message.lower()

    if "not connected" in lower:
        return HTTPException(
            status_code=401,
            detail="Connect your Microsoft account before importing files.",
        )
    if "decrypt" in lower or "no access token" in lower:
        return HTTPException(
            status_code=401,
            detail="Microsoft connection expired. Disconnect and connect again.",
        )
    if "too large" in lower:
        return HTTPException(status_code=413, detail=message)
    if "empty" in lower or "no readable" in lower:
        return HTTPException(
            status_code=422,
            detail="No readable transcript text found in this file.",
        )
    if "not found" in lower:
        return HTTPException(status_code=404, detail=message)

    return HTTPException(status_code=400, detail=message)


def _http_from_graph_status(status_code: int) -> HTTPException:
    if status_code in (401, 403):
        return HTTPException(
            status_code=401,
            detail="Microsoft connection expired or lacks permission. Reconnect your account.",
        )
    if status_code == 404:
        return HTTPException(
            status_code=404,
            detail="File not found in OneDrive.",
        )
    return HTTPException(status_code=502, detail=GRAPH_UNAVAILABLE)


def raise_forbidden(required_permission: str) -> None:
    raise HTTPException(
        status_code=403,
        detail={
            "code": "forbidden",
            "message": "You do not have permission to perform this action.",
            "required_permission": required_permission,
        },
    )


def oauth_redirect_message(code: str | None) -> str:
    """Map Microsoft OAuth error codes to stable frontend message keys."""
    if not code:
        return "unknown"
    normalized = code.strip().lower()
    mapping = {
        "access_denied": "access_denied",
        "consent_required": "consent_required",
        "oauth_failed": "oauth_failed",
        "token_exchange_failed": "token_exchange_failed",
        "invalid_state": "invalid_state",
        "user_not_found": "user_not_found",
    }
    return mapping.get(normalized, "unknown")
