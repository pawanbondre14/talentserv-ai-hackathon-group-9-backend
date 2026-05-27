import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.constants.permissions import INTEGRATIONS_MICROSOFT
from app.dependencies.authz import Principal, require_permission
from app.errors import oauth_redirect_message
from app.config import Settings, get_settings
from app.database import get_db
from app.schemas.teams import MicrosoftStatusResponse
from app.services.microsoft_oauth import (
    build_authorize_url,
    decode_state,
    exchange_code_for_tokens,
    store_refresh_token,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _oauth_redirect(frontend: str, teams: str, message: str) -> RedirectResponse:
    query = urlencode({"teams": teams, "message": message})
    return RedirectResponse(f"{frontend}/new?{query}")


@router.get("/status", response_model=MicrosoftStatusResponse)
def microsoft_status(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_permission(INTEGRATIONS_MICROSOFT)),
    settings: Settings = Depends(get_settings),
):
    user = principal.db_user
    azure_ok = bool(settings.azure_client_id and settings.azure_client_secret)
    return MicrosoftStatusResponse(
        connected=bool(user.ms_refresh_token_enc),
        integration_mode=settings.teams_integration_mode,
        azure_configured=azure_ok,
    )


@router.get("/auth-url")
def microsoft_auth_url(
    principal: Principal = Depends(require_permission(INTEGRATIONS_MICROSOFT)),
    settings: Settings = Depends(get_settings),
):
    if not settings.azure_client_id or not settings.azure_redirect_uri:
        raise HTTPException(
            503,
            detail="Microsoft integration is not configured on the server. Use demo folders or ask an admin to set Azure env vars.",
        )
    url = build_authorize_url(settings, principal.clerk_user_id)
    return {"url": url}


@router.get("/callback")
async def microsoft_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    frontend = settings.frontend_url.rstrip("/")
    if error:
        return _oauth_redirect(frontend, "error", oauth_redirect_message(error))
    if not code or not state:
        raise HTTPException(400, detail="Missing code or state from Microsoft.")

    try:
        clerk_user_id = decode_state(state)
    except Exception as exc:
        raise HTTPException(400, detail="Invalid OAuth state.") from exc

    from app.models import User

    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not user:
        return _oauth_redirect(frontend, "error", "user_not_found")

    try:
        tokens = await exchange_code_for_tokens(settings, code)
        store_refresh_token(settings, user, tokens, db)
        logger.info("Microsoft account connected for user %s", clerk_user_id)
    except ValueError as exc:
        logger.warning("Microsoft OAuth consent issue: %s", exc)
        return _oauth_redirect(frontend, "error", "consent_required")
    except Exception as exc:
        logger.exception("Microsoft OAuth failed")
        return _oauth_redirect(frontend, "error", "token_exchange_failed")

    return _oauth_redirect(frontend, "connected", "connected")


@router.post("/disconnect")
def microsoft_disconnect(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_permission(INTEGRATIONS_MICROSOFT)),
):
    user = principal.db_user
    user.ms_refresh_token_enc = None
    db.commit()
    return {"status": "disconnected"}
