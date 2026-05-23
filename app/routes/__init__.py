from fastapi import APIRouter

from app.routes.health import router as health_router
from app.routes.ingest import router as ingest_router
from app.routes.process import router as process_router
from app.routes.sessions import router as sessions_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(process_router, prefix="/sessions", tags=["process"])
