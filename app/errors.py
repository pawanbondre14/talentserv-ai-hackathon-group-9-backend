from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.auth import AuthUser, get_or_create_db_user

DB_UNAVAILABLE_DETAIL = (
    "Database unavailable. In .env use the Supabase Transaction pooler URI "
    "(host contains pooler.supabase.com, port 6543)."
)


def get_db_user_or_503(db, auth: AuthUser):
    try:
        return get_or_create_db_user(db, auth)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=DB_UNAVAILABLE_DETAIL) from exc
