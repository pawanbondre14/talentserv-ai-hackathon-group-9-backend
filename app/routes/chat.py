import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user, get_or_create_db_user
from app.config import Settings, get_settings
from app.database import get_db
from app.schemas.chat import ChatListResponse, ChatMessageOut, ChatSendRequest, ChatSendResponse
from app.services.chat_service import clear_messages, list_messages, send_message

router = APIRouter()


@router.get("/{session_id}/chat", response_model=ChatListResponse)
def get_chat(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    rows = list_messages(db, user.id, session_id)
    items = [ChatMessageOut.model_validate(r) for r in rows]
    return ChatListResponse(items=items, total=len(items))


@router.post("/{session_id}/chat", response_model=ChatSendResponse)
def post_chat(
    session_id: uuid.UUID,
    body: ChatSendRequest,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    user = get_or_create_db_user(db, auth)
    user_msg, assistant_msg, provider = send_message(
        db, settings, user.id, session_id, body.content
    )
    return ChatSendResponse(
        user_message=ChatMessageOut.model_validate(user_msg),
        assistant_message=ChatMessageOut.model_validate(assistant_msg),
        provider=provider,
    )


@router.delete("/{session_id}/chat")
def delete_chat(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: AuthUser = Depends(get_current_user),
):
    user = get_or_create_db_user(db, auth)
    deleted = clear_messages(db, user.id, session_id)
    return {"deleted": deleted}
