import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user, get_or_create_db_user
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


@router.get("/status", response_model=MicrosoftStatusResponse)
def microsoft_status(
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    user = get_or_create_db_user(db, auth)
    azure_ok = bool(settings.azure_client_id and settings.azure_client_secret)
    return MicrosoftStatusResponse(
        connected=bool(user.ms_refresh_token_enc),
        integration_mode=settings.teams_integration_mode,
        azure_configured=azure_ok,
    )


@router.get("/auth-url")
def microsoft_auth_url(
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    if not settings.azure_client_id or not settings.azure_redirect_uri:
        raise HTTPException(
            503,
            detail="Microsoft integration is not configured. Use mock Teams data or set Azure env vars.",
        )
    get_or_create_db_user(db, auth)
    url = build_authorize_url(settings, auth.clerk_user_id)
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
        return RedirectResponse(f"{frontend}/new?teams=error&message={error}")
    if not code or not state:
        raise HTTPException(400, detail="Missing code or state from Microsoft.")

    try:
        clerk_user_id = decode_state(state)
    except Exception as exc:
        raise HTTPException(400, detail="Invalid OAuth state.") from exc

    from app.models import User

    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not user:
        raise HTTPException(404, detail="User not found for OAuth state.")

    try:
        tokens = await exchange_code_for_tokens(settings, code)
        store_refresh_token(settings, user, tokens, db)
        logger.info("Microsoft account connected for user %s", clerk_user_id)
    except Exception as exc:
        logger.exception("Microsoft OAuth failed")
        return RedirectResponse(f"{frontend}/new?teams=error&message=oauth_failed")

    return RedirectResponse(f"{frontend}/new?teams=connected")


@router.post("/disconnect")
def microsoft_disconnect(
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    user.ms_refresh_token_enc = None
    db.commit()
    return {"status": "disconnected"}
