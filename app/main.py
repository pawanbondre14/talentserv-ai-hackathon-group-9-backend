from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import setup_logging
from app.routes import api_router

settings = get_settings()
setup_logging(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Never connect to Postgres on startup — required for Vercel/Lambda (IPv6 + pooler).
    # Create tables once via supabase/migrations/001_initial_schema.sql in Supabase SQL Editor.
    # Optional local-only: BOOTSTRAP_SCHEMA=true python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
    yield


app = FastAPI(
    title=settings.app_name,
    description="Meeting minutes & interview feedback powered by AI",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }
