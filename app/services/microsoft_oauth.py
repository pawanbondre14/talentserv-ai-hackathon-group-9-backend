import base64
import json
import logging
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.services.token_crypto import encrypt_token

logger = logging.getLogger(__name__)


def _encode_state(clerk_user_id: str) -> str:
    payload = json.dumps({"uid": clerk_user_id})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_state(state: str) -> str:
    raw = base64.urlsafe_b64decode(state.encode())
    data = json.loads(raw.decode())
    return data["uid"]


def build_authorize_url(settings: Settings, clerk_user_id: str) -> str:
    tenant = settings.azure_tenant_id or "common"
    params = {
        "client_id": settings.azure_client_id,
        "response_type": "code",
        "redirect_uri": settings.azure_redirect_uri,
        "response_mode": "query",
        "scope": settings.azure_scopes,
        "state": _encode_state(clerk_user_id),
        "prompt": "consent",
    }
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"


async def exchange_code_for_tokens(settings: Settings, code: str) -> dict:
    tenant = settings.azure_tenant_id or "common"
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    data = {
        "client_id": settings.azure_client_id,
        "client_secret": settings.azure_client_secret,
        "code": code,
        "redirect_uri": settings.azure_redirect_uri,
        "grant_type": "authorization_code",
        "scope": settings.azure_scopes,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, data=data)
        if resp.status_code >= 400:
            logger.error("Microsoft token exchange failed: %s", resp.text)
            resp.raise_for_status()
        return resp.json()


def store_refresh_token(settings: Settings, user, token_payload: dict, db) -> None:
    refresh = token_payload.get("refresh_token")
    if not refresh:
        raise ValueError("Microsoft did not return a refresh token. Try consent again.")
    user.ms_refresh_token_enc = encrypt_token(settings, refresh)
    db.commit()
