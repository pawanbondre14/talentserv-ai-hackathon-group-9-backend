import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user
from app.errors import get_db_user_or_503
from app.config import Settings, get_settings
from app.database import get_db
from app.models import SessionRecord
from app.schemas.session import SessionDetail
from app.schemas.teams import (
    TeamsImportRequest,
    TeamsImportResponse,
    TeamsTranscriptListItem,
    TeamsTranscriptListResponse,
)
from app.services.normalize import normalize_transcript, word_count
from app.services.search_index import build_search_blob
from app.services.teams_service import TeamsService

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
    service = TeamsService(settings)

    try:
        raw_text = await service.fetch_transcript_text(
            user, db, body.meeting_id, body.source
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Teams import failed")
        raise HTTPException(status_code=502, detail=f"Could not fetch transcript: {exc}") from exc

    normalized = normalize_transcript(raw_text)
    wc = word_count(normalized)
    if wc < 1:
        raise HTTPException(400, detail="Transcript is empty after parsing.")

    source_label = "teams" if body.source == "onedrive" else "mock"
    title = body.title
    if not title:
        # resolve title from mock list or use meeting id
        items, _ = await service.list_transcripts(user, db)
        match = next((i for i in items if i.id == body.meeting_id), None)
        title = match.title if match else f"Teams import {body.meeting_id[:8]}"

    session = SessionRecord(
        user_id=user.id,
        title=title[:500],
        mode=body.mode,
        source=source_label,
        status="draft",
        transcript_text=normalized,
        teams_meeting_id=body.meeting_id,
        word_count=wc,
    )
    session.search_vector = build_search_blob(session)
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(
        "Teams import | session_id=%s | source=%s | meeting_id=%s | words=%d",
        session.id,
        source_label,
        body.meeting_id,
        wc,
    )

    return TeamsImportResponse(session=SessionDetail.model_validate(session), word_count=wc)
