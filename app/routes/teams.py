import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user
from app.errors import get_db_user_or_503, http_exception_from_import
from app.config import Settings, get_settings
from app.database import get_db
from app.schemas.teams import (
    TeamsImportRequest,
    TeamsImportResponse,
    TeamsTranscriptListItem,
    TeamsTranscriptListResponse,
)
from app.services.teams_service import TeamsService
from app.services.transcript_import import import_transcript_to_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/transcripts", response_model=TeamsTranscriptListResponse)
async def list_teams_transcripts(
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    user = get_db_user_or_503(db, auth)
    service = TeamsService(settings)
    items, mode = await service.list_transcripts(user, db)
    return TeamsTranscriptListResponse(
        items=[
            TeamsTranscriptListItem(
                id=i.id,
                title=i.title,
                date=i.date,
                source=i.source,
                file_name=i.file_name,
            )
            for i in items
        ],
        integration_mode=mode,
        microsoft_connected=bool(user.ms_refresh_token_enc),
    )


@router.post("/import", response_model=TeamsImportResponse)
async def import_teams_transcript(
    body: TeamsImportRequest,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    user = get_db_user_or_503(db, auth)

    try:
        session, wc = await import_transcript_to_session(
            user,
            db,
            settings,
            item_id=body.meeting_id,
            source=body.source,
            mode=body.mode,
            title=body.title,
        )
    except Exception as exc:
        logger.exception("Teams import failed")
        raise http_exception_from_import(exc) from exc

    return TeamsImportResponse(session=session, word_count=wc)
