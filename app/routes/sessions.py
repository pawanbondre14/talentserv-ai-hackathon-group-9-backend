import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Text, cast, func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth import AuthUser, get_current_user, get_or_create_db_user
from app.database import get_db
from app.models import Output, SessionRecord
from app.schemas import (
    SessionCreate,
    SessionDetail,
    SessionListItem,
    SessionListResponse,
    SessionStatsResponse,
    SessionUpdate,
)
from app.services.search_index import build_search_blob, extract_snippet

router = APIRouter()


def _word_count(text: str | None) -> int:
    if not text or not text.strip():
        return 0
    return len(text.split())


@router.get("", response_model=SessionListResponse)
def list_sessions(
    q: str | None = Query(None, description="Search title, transcript, or AI output"),
    mode: str | None = Query(None),
    status: str | None = Query(None, description="draft|processing|ready|error"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    id_query = (
        db.query(SessionRecord.id, SessionRecord.updated_at)
        .outerjoin(Output, Output.session_id == SessionRecord.id)
        .filter(SessionRecord.user_id == user.id)
    )

    if mode in ("meeting", "interview"):
        id_query = id_query.filter(SessionRecord.mode == mode)

    if status in ("draft", "processing", "ready", "error"):
        id_query = id_query.filter(SessionRecord.status == status)

    if q and q.strip():
        term = f"%{q.strip()}%"
        id_query = id_query.filter(
            or_(
                SessionRecord.title.ilike(term),
                SessionRecord.transcript_text.ilike(term),
                SessionRecord.search_vector.ilike(term),
                cast(Output.edited_json, Text).ilike(term),
                cast(Output.ai_json, Text).ilike(term),
            )
        )

    id_query = id_query.distinct()
    total = id_query.count()
    page = (
        id_query.order_by(SessionRecord.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    session_ids = [row[0] for row in page]
    if not session_ids:
        return SessionListResponse(items=[], total=total, query=q)

    rows_unsorted = (
        db.query(SessionRecord)
        .options(joinedload(SessionRecord.output))
        .filter(SessionRecord.id.in_(session_ids))
        .all()
    )
    order = {sid: idx for idx, sid in enumerate(session_ids)}
    rows = sorted(rows_unsorted, key=lambda r: order.get(r.id, 0))

    items: list[SessionListItem] = []
    for row in rows:
        out = row.output
        items.append(
            SessionListItem(
                id=row.id,
                title=row.title,
                mode=row.mode,
                source=row.source,
                status=row.status,
                word_count=row.word_count,
                created_at=row.created_at,
                updated_at=row.updated_at,
                snippet=extract_snippet(row, out, q),
                has_output=out is not None and (out.edited_json is not None or out.ai_json is not None),
            )
        )

    return SessionListResponse(items=items, total=total, query=q)


@router.get("/stats", response_model=SessionStatsResponse)
def session_stats(
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    base_filter = SessionRecord.user_id == user.id

    total = db.query(func.count(SessionRecord.id)).filter(base_filter).scalar() or 0

    status_counts = dict(
        db.query(SessionRecord.status, func.count(SessionRecord.id))
        .filter(base_filter)
        .group_by(SessionRecord.status)
        .all()
    )

    mode_counts = dict(
        db.query(SessionRecord.mode, func.count(SessionRecord.id))
        .filter(base_filter)
        .group_by(SessionRecord.mode)
        .all()
    )

    total_words = (
        db.query(func.coalesce(func.sum(SessionRecord.word_count), 0))
        .filter(base_filter)
        .scalar()
        or 0
    )

    with_output = (
        db.query(func.count(func.distinct(Output.session_id)))
        .join(SessionRecord, SessionRecord.id == Output.session_id)
        .filter(
            base_filter,
            or_(Output.ai_json.isnot(None), Output.edited_json.isnot(None)),
        )
        .scalar()
        or 0
    )

    return SessionStatsResponse(
        total=total,
        draft=status_counts.get("draft", 0),
        processing=status_counts.get("processing", 0),
        ready=status_counts.get("ready", 0),
        error=status_counts.get("error", 0),
        meeting=mode_counts.get("meeting", 0),
        interview=mode_counts.get("interview", 0),
        with_output=with_output,
        total_words=int(total_words),
    )


@router.post("", response_model=SessionDetail, status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreate,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    transcript = body.transcript_text or ""
    wc = _word_count(transcript)
    title = body.title or (transcript[:80] + "…" if len(transcript) > 80 else transcript) or "Untitled session"

    session = SessionRecord(
        user_id=user.id,
        title=title.strip() or "Untitled session",
        mode=body.mode,
        source=body.source,
        status="draft",
        transcript_text=transcript or None,
        word_count=wc,
    )
    session.search_vector = build_search_blob(session)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    session = (
        db.query(SessionRecord)
        .filter(SessionRecord.id == session_id, SessionRecord.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.patch("/{session_id}", response_model=SessionDetail)
def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    session = (
        db.query(SessionRecord)
        .options(joinedload(SessionRecord.output))
        .filter(SessionRecord.id == session_id, SessionRecord.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if body.title is not None:
        session.title = body.title
    if body.mode is not None:
        session.mode = body.mode
    if body.transcript_text is not None:
        session.transcript_text = body.transcript_text
        session.word_count = _word_count(body.transcript_text)
    if body.status is not None:
        session.status = body.status

    session.search_vector = build_search_blob(session, session.output)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    session = (
        db.query(SessionRecord)
        .filter(SessionRecord.id == session_id, SessionRecord.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    db.delete(session)
    db.commit()
