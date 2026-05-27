import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _engine_kwargs() -> dict:
    url = settings.database_url_resolved
    kwargs: dict = {
        "pool_pre_ping": True,
    }
    connect_args: dict = {"sslmode": "require", "connect_timeout": 15}

    if settings.is_serverless:
        kwargs["poolclass"] = NullPool
        if "db." in url and ".supabase.co" in url and "pooler" not in url:
            logger.warning(
                "Serverless deploy: DATABASE_URL uses db.*.supabase.co which often "
                "fails (IPv6). In Supabase → Database → Connect, use the "
                "Transaction pooler URI (host contains pooler.supabase.com, port 6543)."
            )
    else:
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10

    kwargs["connect_args"] = connect_args
    return kwargs


engine = create_engine(settings.database_url_resolved, **_engine_kwargs())

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
