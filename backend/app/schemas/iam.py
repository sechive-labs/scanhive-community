from pydantic import BaseModel, ConfigDict, EmailStr, Field
from uuid import UUID
from datetime import datetime


class RoleSummary(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str
    permissions: list[str]
    is_system: bool
    locked: bool
    included_roles: list[RoleSummary] = Field(default_factory=list)
    effective_permissions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool
    effective_permissions: list[str] = Field(default_factory=list)
    roles: list[RoleResponse] = Field(default_factory=list)
    organization_id: int
    organization_name: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default="", max_length=100)


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    permissions: list[str] = Field(default_factory=list, max_length=100)
    included_role_ids: list[int] = Field(default_factory=list, max_length=50)


class RoleUpdate(RoleCreate):
    pass


class UserRoleAssignment(BaseModel):
    role_ids: list[int] = Field(default_factory=list)


class UserAdminUpdate(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default="", max_length=100)
    is_active: bool
    role_ids: list[int] = Field(default_factory=list)


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    user_ids: list[int] = Field(default_factory=list)


class GroupUpdate(GroupCreate):
    role_ids: list[int] = Field(default_factory=list)
    project_ids: list[UUID] = Field(default_factory=list)


class GroupItemResponse(BaseModel):
    id: int | UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: str
    created_by: str | None
    users: list[GroupItemResponse] = Field(default_factory=list)
    roles: list[GroupItemResponse] = Field(default_factory=list)
    projects: list[GroupItemResponse] = Field(default_factory=list)


class GroupResourcesResponse(BaseModel):
    projects: list[GroupItemResponse] = Field(default_factory=list)


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class InvitationCreate(BaseModel):
    email: EmailStr
    role_ids: list[int] = Field(default_factory=list)


class InvitationResponse(BaseModel):
    id: int
    email: EmailStr
    status: str
    token: str
    roles: list[RoleResponse] = Field(default_factory=list)
    invited_by: str | None = None
    created_at: datetime
    expires_at: datetime
    email_sent: bool | None = None
