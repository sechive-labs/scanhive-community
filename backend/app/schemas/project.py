from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from uuid import UUID


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    owner_id: int

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(ProjectResponse):
    total_vulnerabilities: int
    last_scan: datetime | None
    scanners: list[str] | None
    critical: int
    high: int
    medium: int
    low: int
    info: int


class ProjectAccessAssignment(BaseModel):
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class ProjectAccessUpdate(BaseModel):
    assignments: list[ProjectAccessAssignment] = Field(default_factory=list)
    group_ids: list[int] = Field(default_factory=list)


class ProjectAccessUser(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    effective_role_names: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ProjectAccessGroup(BaseModel):
    id: int
    name: str
    description: str | None
    member_count: int
    effective_role_names: list[str] = Field(default_factory=list)


class ProjectAccessResponse(BaseModel):
    users: list[ProjectAccessUser]
    assignments: list[ProjectAccessAssignment]
    groups: list[ProjectAccessGroup]
    group_ids: list[int]
