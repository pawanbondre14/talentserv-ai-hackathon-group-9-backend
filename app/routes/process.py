import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth import AuthUser, get_current_user, get_or_create_db_user
from app.config import Settings, get_settings
from app.database import get_db
from app.errors import AI_PROCESSING_FAILED
from app.models import Output, SessionRecord
from app.routes.sessions import _word_count
from app.services.search_index import build_search_blob
from app.schemas.interview import ProcessRequest
from app.schemas.output import InterviewMetaOut, OutputSchema, OutputUpdate, ProcessResponse, SessionWithOutput
from app.schemas.session import SessionDetail
from app.services.graph_runner import run_analysis
from app.services.interview_processor import save_interview_meta_for_session
from app.services.llm import _should_mock
from app.services.normalize import normalize_transcript, truncate_transcript, word_count

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_user_session(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> SessionRecord:
    session = (
        db.query(SessionRecord)
        .options(
            joinedload(SessionRecord.output),
            joinedload(SessionRecord.interview_meta),
        )
        .filter(SessionRecord.id == session_id, SessionRecord.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.get("/{session_id}/full", response_model=SessionWithOutput)
def get_session_with_output(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    session = _get_user_session(db, user.id, session_id)
    out = session.output
    payload = SessionDetail.model_validate(session).model_dump()
    payload["output"] = OutputSchema.model_validate(out) if out else None
    meta = session.interview_meta
    payload["interview_meta"] = InterviewMetaOut.model_validate(meta) if meta else None
    return payload


@router.post("/{session_id}/process", response_model=ProcessResponse)
def process_session(
    session_id: uuid.UUID,
    body: ProcessRequest | None = None,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    user = get_or_create_db_user(db, auth)
    session = _get_user_session(db, user.id, session_id)

    raw = session.transcript_text or ""
    normalized = normalize_transcript(raw)
    wc = word_count(normalized)
    if wc < settings.min_transcript_words:
        raise HTTPException(
            status_code=400,
            detail=f"Transcript needs at least {settings.min_transcript_words} words (found {wc}).",
        )

    text, truncated = truncate_transcript(normalized, settings.max_transcript_chars)
    session.status = "processing"
    db.commit()

    mode_label = "Interview Feedback" if session.mode == "interview" else "Meeting Minutes"
    provider = "mock" if _should_mock(settings) else settings.llm_provider
    logger.info(
        "AI process requested | session_id=%s | mode=%s (%s) | user=%s | words=%d | provider=%s | truncated=%s",
        session_id,
        session.mode,
        mode_label,
        auth.clerk_user_id,
        wc,
        provider,
        truncated,
    )

    interview_options = body.interview_options if body else None
    strategy = body.strategy if body else "auto"
    if session.mode == "interview":
        save_interview_meta_for_session(db, session, interview_options)

    pipeline = "langgraph" if settings.langgraph_enabled else "legacy"
    logger.info(
        "AI pipeline=%s | session_id=%s | strategy=%s",
        pipeline,
        session_id,
        strategy,
    )

    started = time.perf_counter()
    try:
        result = run_analysis(
            settings,
            session_id=str(session_id),
            mode=session.mode,
            transcript=text,
            interview_options=interview_options,
            strategy=strategy,
            word_count=wc,
            truncated=truncated,
        )

        output_row = session.output
        if output_row:
            output_row.ai_json = result
            output_row.edited_json = result
        else:
            output_row = Output(session_id=session.id, ai_json=result, edited_json=result)
            db.add(output_row)

        session.status = "ready"
        session.transcript_text = normalized
        session.word_count = wc
        session.search_vector = build_search_blob(session, output_row)
        db.commit()
        db.refresh(session)
        db.refresh(output_row)

        elapsed = time.perf_counter() - started
        logger.info(
            "AI process completed | session_id=%s | mode=%s (%s) | status=ready | provider=%s | elapsed=%.2fs",
            session_id,
            session.mode,
            mode_label,
            provider,
            elapsed,
        )

        return ProcessResponse(
            session=SessionDetail.model_validate(session),
            output=OutputSchema.model_validate(output_row),
            provider=provider,
            truncated=truncated,
        )
    except HTTPException as exc:
        session.status = "error"
        db.commit()
        elapsed = time.perf_counter() - started
        logger.error(
            "AI process failed | session_id=%s | mode=%s (%s) | http_status=%s | detail=%s | elapsed=%.2fs",
            session_id,
            session.mode,
            mode_label,
            exc.status_code,
            exc.detail,
            elapsed,
        )
        raise
    except Exception as exc:
        session.status = "error"
        db.commit()
        elapsed = time.perf_counter() - started
        logger.exception(
            "AI process failed | session_id=%s | mode=%s (%s) | elapsed=%.2fs",
            session_id,
            session.mode,
            mode_label,
            elapsed,
        )
        raise HTTPException(status_code=502, detail=AI_PROCESSING_FAILED) from exc


@router.patch("/{session_id}/output", response_model=OutputSchema)
def update_output(
    session_id: uuid.UUID,
    body: OutputUpdate,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    session = _get_user_session(db, user.id, session_id)
    if not session.output:
        raise HTTPException(status_code=404, detail="No output for this session. Run process first.")

    session.output.edited_json = body.edited_json
    session.search_vector = build_search_blob(session, session.output)
    db.commit()
    db.refresh(session.output)
    return session.output
