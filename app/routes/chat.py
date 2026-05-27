import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.constants.permissions import CHAT_USE
from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies.authz import Principal, get_session_for_principal, require_permission
from app.schemas.chat import ChatListResponse, ChatMessageOut, ChatSendRequest, ChatSendResponse
from app.services.chat_service import clear_messages_for_session, list_messages_for_session, send_message_for_session

router = APIRouter()


@router.get("/{session_id}/chat", response_model=ChatListResponse)
def get_chat(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_permission(CHAT_USE)),
):
    get_session_for_principal(db, principal, session_id, read=True)
    rows = list_messages_for_session(db, session_id)
    items = [ChatMessageOut.model_validate(r) for r in rows]
    return ChatListResponse(items=items, total=len(items))


@router.post("/{session_id}/chat", response_model=ChatSendResponse)
def post_chat(
    session_id: uuid.UUID,
    body: ChatSendRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_permission(CHAT_USE)),
    settings: Settings = Depends(get_settings),
):
    get_session_for_principal(db, principal, session_id, read=True)
    user_msg, assistant_msg, provider = send_message_for_session(
        db, settings, session_id, body.content
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
    principal: Principal = Depends(require_permission(CHAT_USE)),
):
    get_session_for_principal(db, principal, session_id, read=True)
    deleted = clear_messages_for_session(db, session_id)
    return {"deleted": deleted}
