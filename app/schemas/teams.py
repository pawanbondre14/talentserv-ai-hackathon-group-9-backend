from typing import Literal

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


class OneDriveBreadcrumbItem(BaseModel):
    id: str
    name: str


class OneDriveBrowseItem(BaseModel):
    id: str
    name: str
    kind: Literal["folder", "file"]
    size: int | None = None
    modified_at: str | None = None
    extension: str | None = None


class OneDriveBrowseResponse(BaseModel):
    folder_id: str
    folder_name: str
    breadcrumb: list[OneDriveBreadcrumbItem]
    items: list[OneDriveBrowseItem]
    integration_mode: str
    microsoft_connected: bool


class OneDriveImportRequest(BaseModel):
    item_id: str
    source: Literal["mock", "onedrive"] = "onedrive"
    mode: Literal["meeting", "interview"] = "meeting"
    title: str | None = None
    file_name: str | None = None


class OneDriveImportResponse(BaseModel):
    session: SessionDetail
    word_count: int
