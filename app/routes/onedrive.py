import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user
from app.config import Settings, get_settings
from app.database import get_db
from app.errors import get_db_user_or_503
from app.schemas.teams import (
    OneDriveBrowseItem,
    OneDriveBrowseResponse,
    OneDriveImportRequest,
    OneDriveImportResponse,
    TeamsTranscriptListItem,
    TeamsTranscriptListResponse,
)
from app.services.teams_service import TeamsService
from app.services.transcript_import import import_transcript_to_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/browse", response_model=OneDriveBrowseResponse)
async def browse_onedrive_folder(
    folder_id: str = Query(default="root"),
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    user = get_db_user_or_503(db, auth)
    service = TeamsService(settings)
    result = await service.browse_folder(user, db, folder_id)
    return OneDriveBrowseResponse(
        folder_id=result.folder_id,
        folder_name=result.folder_name,
        breadcrumb=[],
        items=[
            OneDriveBrowseItem(
                id=i.id,
                name=i.name,
                kind=i.kind,
                size=i.size,
                modified_at=i.modified_at,
                extension=i.extension,
            )
            for i in result.items
        ],
        integration_mode=result.integration_mode,
        microsoft_connected=bool(user.ms_refresh_token_enc),
    )


@router.get("/recordings", response_model=TeamsTranscriptListResponse)
async def list_onedrive_recordings(
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


@router.post("/import", response_model=OneDriveImportResponse)
async def import_onedrive_file(
    body: OneDriveImportRequest,
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
            item_id=body.item_id,
            source=body.source,
            mode=body.mode,
            title=body.title,
            file_name=body.file_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("OneDrive import failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return OneDriveImportResponse(session=session, word_count=wc)
