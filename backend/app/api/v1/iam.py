from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db, translate_integrity_error
from app.models.user import User
from app.models.role import Role
from app.models.group import Group
from app.models.project import Project
from app.models.organization import Organization
from app.models.invitation import Invitation
from app.services.invitation_service import InvitationService, InvitationNotFoundError, DuplicateInvitationEmailError
from app.repositories.user_repository import UserRepository
from app.schemas.iam import (
    RoleResponse,
    RoleCreate,
    RoleUpdate,
    UserProfileResponse,
    UserProfileUpdate,
    UserRoleAssignment,
    UserAdminUpdate,
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupResourcesResponse,
    OrganizationResponse,
    OrganizationUpdate,
    InvitationCreate,
    InvitationResponse,
)

router = APIRouter(
    prefix="/api/v1/iam",
    tags=["Identity and Access Management"],
)


@router.get("/organization", response_model=OrganizationResponse)
def get_organization(current_user: User = Depends(get_current_user)):
    return current_user.organization


@router.put("/organization", response_model=OrganizationResponse)
def update_organization(
    request: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.users.manage")
    organization = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()
    organization.name = request.name.strip()
    db.commit()
    db.refresh(organization)
    return organization


def serialize_invitation(invitation: Invitation, email_sent: bool | None = None) -> dict:
    return {
        "id": invitation.id,
        "email": invitation.email,
        "status": invitation.status,
        "token": invitation.token,
        "roles": invitation.roles,
        "invited_by": invitation.invited_by.email if invitation.invited_by else None,
        "created_at": invitation.created_at,
        "expires_at": invitation.expires_at,
        "email_sent": email_sent,
    }


@router.get("/invitations", response_model=list[InvitationResponse])
def list_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.users.manage")
    invitations = InvitationService(db).list_invitations(current_user.organization_id)
    return [serialize_invitation(invitation) for invitation in invitations]


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    request: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.users.manage", "iam.users.create")
    try:
        invitation, email_sent = InvitationService(db).create(
            current_user.organization_id, request.email, request.role_ids, current_user,
        )
    except DuplicateInvitationEmailError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return serialize_invitation(invitation, email_sent)


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.users.manage", "iam.users.delete")
    try:
        InvitationService(db).revoke(invitation_id, current_user.organization_id)
    except InvitationNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    request: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.first_name = request.first_name.strip()
    current_user.last_name = request.last_name.strip()

    with translate_integrity_error(db, "Unable to update profile"):
        return UserRepository(db).update(current_user)


@router.get("/users", response_model=list[UserProfileResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.users.manage")
    return UserRepository(db).get_all(current_user.organization_id)


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_iam_access(current_user)
    return db.query(Role).filter(Role.organization_id == current_user.organization_id).order_by(Role.id.asc()).all()


def normalize_permissions(permissions: list[str]) -> list[str]:
    return sorted({permission.strip() for permission in permissions if permission.strip()})


def validate_role_permissions(permissions: list[str]) -> list[str]:
    return normalize_permissions(permissions)


def require_iam_access(user: User) -> None:
    if not any(
        permission.startswith("iam.")
        for permission in user.effective_permissions
    ):
        raise HTTPException(403, "IAM administration access required")


def serialize_group(group: Group) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_at": group.created_at.isoformat(),
        "created_by": group.created_by.email if group.created_by else None,
        "users": group.users,
        "roles": group.roles,
        "projects": group.projects,
    }


def get_records(db: Session, model, ids: list[int], label: str, organization_id: int):
    unique_ids = set(ids)
    records = db.query(model).filter(
        model.id.in_(unique_ids),
        model.organization_id == organization_id,
    ).all() if ids else []
    if len(records) != len(unique_ids):
        raise HTTPException(400, f"One or more {label} do not exist")
    return records


def validate_no_role_cycle(role: Role | None, proposed_included_roles: list[Role]) -> None:
    """Reject `proposed_included_roles` if including them on `role` would create a cycle.

    `role` is None when creating a brand new role, which can't be part of an
    existing cycle yet.
    """
    if role is None:
        return
    stack = list(proposed_included_roles)
    seen: set[int] = set()
    while stack:
        candidate = stack.pop()
        if candidate.id == role.id:
            raise HTTPException(
                400,
                f"'{candidate.name}' cannot be included here -- it would create a circular role reference",
            )
        if candidate.id in seen:
            continue
        seen.add(candidate.id)
        stack.extend(candidate.included_roles)


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    request: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.roles.manage")
    included_roles = get_records(db, Role, request.included_role_ids, "roles", current_user.organization_id)
    role = Role(
        name=request.name.strip(),
        description=request.description.strip(),
        permissions=validate_role_permissions(request.permissions),
        included_roles=included_roles,
        is_system=False,
        organization_id=current_user.organization_id,
    )
    db.add(role)

    with translate_integrity_error(db, "Role name already exists"):
        db.commit()
        db.refresh(role)
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    request: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.roles.manage")
    role = db.query(Role).filter(Role.id == role_id, Role.organization_id == current_user.organization_id).first()

    if role is None:
        raise HTTPException(404, "Role not found")

    if role.locked:
        raise HTTPException(400, "This is a default role and cannot be edited")

    included_roles = get_records(db, Role, request.included_role_ids, "roles", current_user.organization_id)
    validate_no_role_cycle(role, included_roles)

    role.name = request.name.strip()
    role.description = request.description.strip()
    role.permissions = validate_role_permissions(request.permissions)
    role.included_roles = included_roles

    with translate_integrity_error(db, "Role name already exists"):
        db.commit()
        db.refresh(role)
    return role


@router.get("/roles/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_iam_access(current_user)
    role = db.query(Role).filter(Role.id == role_id, Role.organization_id == current_user.organization_id).first()

    if role is None:
        raise HTTPException(404, "Role not found")

    return role


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.roles.manage")
    role = db.query(Role).filter(Role.id == role_id, Role.organization_id == current_user.organization_id).first()

    if role is None:
        raise HTTPException(404, "Role not found")

    if role.locked:
        raise HTTPException(400, "This is a default role and cannot be deleted")

    db.delete(role)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/users/{user_id}/roles",
    response_model=UserProfileResponse,
)
def assign_user_roles(
    user_id: int,
    request: UserRoleAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.users.manage", "iam.users.update")
    user = db.query(User).filter(User.id == user_id, User.organization_id == current_user.organization_id).first()

    if user is None:
        raise HTTPException(404, "User not found")

    roles = (
        db.query(Role)
        .filter(Role.id.in_(set(request.role_ids)), Role.organization_id == current_user.organization_id)
        .all()
        if request.role_ids
        else []
    )

    if len(roles) != len(set(request.role_ids)):
        raise HTTPException(400, "One or more roles do not exist")

    if user.id == current_user.id and not any(
        "iam.users.manage" in role.effective_permissions
        for role in roles
    ):
        raise HTTPException(400, "You cannot remove your own IAM access")

    user.roles = roles
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserProfileResponse)
def update_user(
    user_id: int,
    request: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.users.manage", "iam.users.update")
    user = db.query(User).filter(User.id == user_id, User.organization_id == current_user.organization_id).first()
    if user is None:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id and not request.is_active:
        raise HTTPException(400, "You cannot disable your own account")

    roles = get_records(db, Role, request.role_ids, "roles", current_user.organization_id)
    group_keeps_iam_access = any(
        "iam.users.manage" in role.effective_permissions
        for group in user.groups
        for role in group.roles
    )
    if user.id == current_user.id and not group_keeps_iam_access and not any(
        "iam.users.manage" in role.effective_permissions for role in roles
    ):
        raise HTTPException(400, "You cannot remove your own IAM access")

    user.email = request.email.lower()
    user.first_name = request.first_name.strip()
    user.last_name = request.last_name.strip()
    user.is_active = request.is_active
    user.roles = roles
    with translate_integrity_error(db, "Email address already exists"):
        db.commit()
        db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserProfileResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.users.manage")
    user = db.query(User).filter(User.id == user_id, User.organization_id == current_user.organization_id).first()
    if user is None:
        raise HTTPException(404, "User not found")
    return user


@router.get("/groups", response_model=list[GroupResponse])
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.groups.manage")
    groups = db.query(Group).filter(Group.organization_id == current_user.organization_id).order_by(Group.name.asc()).all()
    return [serialize_group(group) for group in groups]


@router.get("/group-resources", response_model=GroupResourcesResponse)
def list_group_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.groups.manage")
    return {
        "projects": db.query(Project).filter(Project.organization_id == current_user.organization_id).order_by(Project.name.asc()).all(),
    }


@router.post(
    "/groups",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    request: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.groups.manage")
    group = Group(
        name=request.name.strip(),
        description=request.description.strip() if request.description else None,
        created_by_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    group.users = get_records(db, User, request.user_ids, "users", current_user.organization_id)
    db.add(group)

    with translate_integrity_error(db, "Group name already exists"):
        db.commit()
        db.refresh(group)

    return serialize_group(group)


@router.put("/groups/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    request: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.groups.manage")
    group = db.query(Group).filter(Group.id == group_id, Group.organization_id == current_user.organization_id).first()
    if group is None:
        raise HTTPException(404, "Group not found")

    group.name = request.name.strip()
    group.description = request.description.strip() if request.description else None
    group.users = get_records(db, User, request.user_ids, "users", current_user.organization_id)
    group.roles = get_records(db, Role, request.role_ids, "roles", current_user.organization_id)
    group.projects = get_records(db, Project, request.project_ids, "projects", current_user.organization_id)
    with translate_integrity_error(db, "Group name already exists"):
        db.commit()
        db.refresh(group)
    return serialize_group(group)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "iam.groups.manage")
    group = db.query(Group).filter(Group.id == group_id, Group.organization_id == current_user.organization_id).first()
    if group is None:
        raise HTTPException(404, "Group not found")
    db.delete(group)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
