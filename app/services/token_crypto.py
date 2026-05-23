import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings


def _fernet(settings: Settings) -> Fernet | None:
    key = settings.ms_token_encryption_key.strip()
    if not key:
        return None
    try:
        return Fernet(key.encode() if not key.startswith("gAAAA") else key)
    except Exception:
        # Derive a Fernet key from arbitrary secret string
        digest = hashlib.sha256(key.encode()).digest()
        fkey = base64.urlsafe_b64encode(digest)
        return Fernet(fkey)


def encrypt_token(settings: Settings, plain: str) -> str:
    f = _fernet(settings)
    if f is None:
        return base64.b64encode(plain.encode()).decode()
    return f.encrypt(plain.encode()).decode()


def decrypt_token(settings: Settings, stored: str) -> str:
    f = _fernet(settings)
    if f is None:
        return base64.b64decode(stored.encode()).decode()
    try:
        return f.decrypt(stored.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Could not decrypt Microsoft token.") from exc
