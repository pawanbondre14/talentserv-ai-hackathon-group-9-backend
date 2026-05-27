from fastapi import APIRouter

from app.routes.admin import router as admin_router
from app.routes.chat import router as chat_router
from app.routes.interview import router as interview_router
from app.routes.health import router as health_router
from app.routes.ingest import router as ingest_router
from app.routes.me import router as me_router
from app.routes.microsoft import router as microsoft_router
from app.routes.onedrive import router as onedrive_router
from app.routes.process import router as process_router
from app.routes.sessions import router as sessions_router
from app.routes.teams import router as teams_router

api_router = APIRouter()
api_router.include_router(me_router, tags=["auth"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
api_router.include_router(microsoft_router, prefix="/microsoft", tags=["microsoft"])
api_router.include_router(onedrive_router, prefix="/onedrive", tags=["onedrive"])
api_router.include_router(teams_router, prefix="/teams", tags=["teams"])
api_router.include_router(interview_router, prefix="/interview", tags=["interview"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(process_router, prefix="/sessions", tags=["process"])
api_router.include_router(chat_router, prefix="/sessions", tags=["chat"])
