from dataclasses import dataclass

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import Settings, get_settings

security = HTTPBearer(auto_error=False)

_jwks_client: PyJWKClient | None = None


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


@dataclass
class AuthUser:
    clerk_user_id: str
    email: str | None = None


def _normalize_issuer(issuer: str) -> str:
    return issuer.rstrip("/")


def verify_clerk_token(token: str, settings: Settings) -> AuthUser:
    if not settings.clerk_jwks_url or not settings.clerk_issuer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk is not configured on the server.",
        )

    issuer = _normalize_issuer(settings.clerk_issuer)
    jwks_url = settings.clerk_jwks_url.rstrip("/")
    if not jwks_url.endswith("/.well-known/jwks.json"):
        jwks_url = f"{issuer}/.well-known/jwks.json"

    try:
        client = _get_jwks_client(jwks_url)
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            leeway=60,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Invalid or expired Clerk session. Sign in again at the app (not via /docs). "
                f"Verify CLERK_ISSUER matches your Clerk dashboard ({issuer})."
            ),
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

    email = payload.get("email")
    if not email and isinstance(payload.get("email_addresses"), list):
        emails = payload["email_addresses"]
        if emails:
            email = emails[0]

    return AuthUser(clerk_user_id=sub, email=email)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> AuthUser:
    if settings.skip_auth:
        return AuthUser(clerk_user_id=settings.dev_user_id, email="dev@local.test")

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Authentication required. Sign in at the React app first, then use "
                "'Connect Microsoft account' — do not open /api/microsoft/auth-url in the browser."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_clerk_token(credentials.credentials, settings)


def get_or_create_db_user(db, auth_user: AuthUser):
    from app.models import User

    user = db.query(User).filter(User.clerk_user_id == auth_user.clerk_user_id).first()
    if user:
        if auth_user.email and user.email != auth_user.email:
            user.email = auth_user.email
            db.commit()
            db.refresh(user)
        return user

    user = User(clerk_user_id=auth_user.clerk_user_id, email=auth_user.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
