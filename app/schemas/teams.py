from pydantic import BaseModel, Field

from app.schemas.session import SessionDetail


class TeamsTranscriptListItem(BaseModel):
    id: str
    title: str
    date: str
    source: str
    file_name: str | None = None


class TeamsTranscriptListResponse(BaseModel):
    items: list[TeamsTranscriptListItem]
    integration_mode: str  # mock | live
    microsoft_connected: bool


class TeamsImportRequest(BaseModel):
    meeting_id: str
    source: str = Field(pattern="^(mock|onedrive)$")
    mode: str = Field(default="meeting", pattern="^(meeting|interview)$")
    title: str | None = None


class TeamsImportResponse(BaseModel):
    session: SessionDetail
    word_count: int


class MicrosoftStatusResponse(BaseModel):
    connected: bool
    integration_mode: str
    azure_configured: bool
