from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str | None = None
    mode: str = Field(default="meeting", pattern="^(meeting|interview)$")
    source: str = Field(default="paste", pattern="^(paste|upload|teams|mock)$")
    transcript_text: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    mode: str | None = Field(default=None, pattern="^(meeting|interview)$")
    transcript_text: str | None = None
    status: str | None = None


class SessionListItem(BaseModel):
    id: UUID
    title: str
    mode: str
    source: str
    status: str
    word_count: int
    created_at: datetime
    updated_at: datetime
    snippet: str | None = None
    has_output: bool = False

    model_config = {"from_attributes": True}


class SessionDetail(SessionListItem):
    transcript_text: str | None = None
    teams_meeting_id: str | None = None

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    items: list[SessionListItem]
    total: int
    query: str | None = None
