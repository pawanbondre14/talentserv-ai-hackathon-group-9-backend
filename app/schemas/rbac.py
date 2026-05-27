import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MeUserOut(BaseModel):
    id: uuid.UUID
    clerk_user_id: str
    email: str | None
    display_name: str | None

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: MeUserOut
    roles: list[str]
    permissions: list[str]


class AssignRoleRequest(BaseModel):
    role_name: str = Field(..., min_length=1, max_length=64)


class PermissionOverrideRequest(BaseModel):
    permission_key: str = Field(..., min_length=1, max_length=128)
    effect: str = Field(..., pattern="^(grant|deny)$")


class RoleOut(BaseModel):
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class UserRbacOut(BaseModel):
    user_id: uuid.UUID
    roles: list[str]
    permissions: list[str]
    overrides: list[dict[str, str]] = []
