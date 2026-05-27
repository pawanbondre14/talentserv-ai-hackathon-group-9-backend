from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatListResponse(BaseModel):
    items: list[ChatMessageOut]
    total: int


class ChatSendRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class ChatSendResponse(BaseModel):
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    provider: str
