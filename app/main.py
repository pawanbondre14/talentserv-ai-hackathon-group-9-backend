import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.errors import DB_UNAVAILABLE_DETAIL
from app.logging_config import setup_logging
from app.routes import api_router

logger = logging.getLogger(__name__)
settings = get_settings()
setup_logging(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.skip_auth:
        logger.warning("SKIP_AUTH=true — authentication disabled (local dev only)")
    elif not s.clerk_issuer or not s.clerk_jwks_url:
        logger.error(
            "Clerk is not configured. Set CLERK_ISSUER and CLERK_JWKS_URL in backend .env "
            "(must match frontend VITE_CLERK_PUBLISHABLE_KEY), then restart the server."
        )
    else:
        logger.info("Clerk auth configured (issuer=%s)", s.clerk_issuer.rstrip("/"))
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


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(_request: Request, exc: SQLAlchemyError):
    logger.exception("Database error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": DB_UNAVAILABLE_DETAIL},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=dict(exc.headers or {}),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }
