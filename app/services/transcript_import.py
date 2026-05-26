import logging

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import SessionRecord
from app.schemas.session import SessionDetail
from app.services.normalize import normalize_transcript, word_count
from app.services.search_index import build_search_blob
from app.services.teams_service import TeamsService

logger = logging.getLogger(__name__)


async def import_transcript_to_session(
    user,
    db: Session,
    settings: Settings,
    *,
    item_id: str,
    source: str,
    mode: str,
    title: str | None = None,
    file_name: str | None = None,
) -> tuple[SessionDetail, int]:
    service = TeamsService(settings)

    try:
        raw_text = await service.fetch_transcript_text(user, db, item_id, source)
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Could not fetch transcript: {exc}") from exc

    normalized = normalize_transcript(raw_text)
    wc = word_count(normalized)
    if wc < 1:
        raise ValueError("Transcript is empty after parsing.")

    if source == "mock":
        source_label = "mock"
    else:
        source_label = "onedrive"

    session_title = title
    if not session_title:
        if file_name:
            session_title = file_name.rsplit(".", 1)[0]
        else:
            items, _ = await service.list_transcripts(user, db)
            match = next((i for i in items if i.id == item_id), None)
            session_title = match.title if match else f"OneDrive import {item_id[:8]}"

    session = SessionRecord(
        user_id=user.id,
        title=session_title[:500],
        mode=mode,
        source=source_label,
        status="draft",
        transcript_text=normalized,
        teams_meeting_id=item_id,
        word_count=wc,
    )
    session.search_vector = build_search_blob(session)
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(
        "OneDrive import | session_id=%s | source=%s | item_id=%s | words=%d",
        session.id,
        source_label,
        item_id,
        wc,
    )

    return SessionDetail.model_validate(session), wc
