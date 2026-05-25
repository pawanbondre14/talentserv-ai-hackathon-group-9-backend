import json
import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.models import ChatMessage, SessionRecord
from app.prompts.session_chat import SESSION_CHAT_SYSTEM, session_chat_context_block
from app.services.llm import complete_chat

logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_CHARS = 14_000
MAX_OUTPUT_JSON_CHARS = 10_000
MAX_JD_CHARS = 4_000


def _get_session_for_user(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID
) -> SessionRecord:
    session = (
        db.query(SessionRecord)
        .filter(SessionRecord.id == session_id, SessionRecord.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


def list_messages(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> list[ChatMessage]:
    _get_session_for_user(db, user_id, session_id)
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


def clear_messages(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> int:
    _get_session_for_user(db, user_id, session_id)
    count = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return count


def _build_system_prompt(session: SessionRecord) -> str:
    transcript = (session.transcript_text or "").strip()
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n...[truncated]"

    output_json = "No structured output yet."
    if session.output:
        data = session.output.edited_json or session.output.ai_json
        if data:
            dumped = json.dumps(data, indent=2)
            if len(dumped) > MAX_OUTPUT_JSON_CHARS:
                dumped = dumped[:MAX_OUTPUT_JSON_CHARS] + "\n...[truncated]"
            output_json = dumped

    jd_excerpt = None
    if session.interview_meta and session.interview_meta.jd_text:
        jd = session.interview_meta.jd_text.strip()
        jd_excerpt = jd[:MAX_JD_CHARS] + ("..." if len(jd) > MAX_JD_CHARS else "")

    context = session_chat_context_block(
        session.title,
        session.mode,
        transcript or "(empty)",
        output_json,
        jd_excerpt,
    )
    return f"{SESSION_CHAT_SYSTEM}\n\n--- SESSION CONTEXT ---\n{context}"


def send_message(
    db: Session,
    settings: Settings,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    content: str,
) -> tuple[ChatMessage, ChatMessage, str]:
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

    if session.status != "ready" or not session.output:
        raise HTTPException(
            status_code=400,
            detail="Generate AI output for this session before using chat.",
        )

    user_row = ChatMessage(session_id=session_id, role="user", content=content.strip())
    db.add(user_row)
    db.flush()

    prior = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.id != user_row.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in prior]

    system = _build_system_prompt(session)
    reply_text, provider = complete_chat(
        settings,
        system,
        history,
        content.strip(),
        session_id=str(session_id),
    )

    assistant_row = ChatMessage(session_id=session_id, role="assistant", content=reply_text)
    db.add(assistant_row)
    db.commit()
    db.refresh(user_row)
    db.refresh(assistant_row)

    logger.info(
        "Chat message saved | session_id=%s | provider=%s | user_chars=%d | reply_chars=%d",
        session_id,
        provider,
        len(content),
        len(reply_text),
    )
    return user_row, assistant_row, provider
