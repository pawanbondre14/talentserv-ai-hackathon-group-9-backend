from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.session import SessionDetail


class OutputSchema(BaseModel):
    id: UUID
    session_id: UUID
    ai_json: dict[str, Any] | None = None
    edited_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OutputUpdate(BaseModel):
    edited_json: dict[str, Any] = Field(..., description="User-edited structured output")


class ProcessResponse(BaseModel):
    session: SessionDetail
    output: OutputSchema
    provider: str
    truncated: bool = False


class SessionWithOutput(SessionDetail):
    output: OutputSchema | None = None

    model_config = {"from_attributes": True}
