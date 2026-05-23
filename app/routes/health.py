from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/health/db")
def health_db(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
):
    if settings.is_serverless and settings.uses_direct_supabase_host:
        return {
            "status": "error",
            "database": (
                "DATABASE_URL uses db.*.supabase.co — Vercel cannot reach it (IPv6). "
                "In Supabase → Connect → ORMs → Transaction (6543), copy the URI whose "
                "host is aws-0-REGION.pooler.supabase.com and set that as DATABASE_URL. "
                "Encode @ in password as %40."
            ),
        }
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        msg = str(exc)
        if "Cannot assign requested address" in msg and settings.uses_direct_supabase_host:
            msg += (
                " — Switch DATABASE_URL to the Supabase pooler host "
                "(pooler.supabase.com), not db.*.supabase.co."
            )
        return {"status": "error", "database": msg}
