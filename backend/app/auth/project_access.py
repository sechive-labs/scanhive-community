from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.associations import group_projects, group_users
from app.models.project_access import ProjectAccess


def _has_explicit_project_access(db: Session, user, project) -> bool:
    access = db.query(ProjectAccess).filter(
        ProjectAccess.project_id == project.id,
        ProjectAccess.user_id == user.id,
    ).first()
    group_access = db.query(group_projects.c.project_id).join(
        group_users,
        group_users.c.group_id == group_projects.c.group_id,
    ).filter(
        group_projects.c.project_id == project.id,
        group_users.c.user_id == user.id,
    ).first()
    return bool(access or group_access)


def project_permissions(db: Session, user, project) -> set[str]:
    if project.organization_id != user.organization_id:
        return set()
    if project.owner_id == user.id:
        return {"*"}
    return set(user.effective_permissions) if _has_explicit_project_access(db, user, project) else set()


def require_project_permission(db: Session, user, project, *permissions: str) -> None:
    if project.organization_id != user.organization_id:
        raise HTTPException(404, "Project not found")
    granted = project_permissions(db, user, project)
    if "*" not in granted and not granted.intersection(permissions):
        raise HTTPException(403, "You do not have permission for this project action")


def require_project_access(db: Session, user, project) -> None:
    """Anyone with access to a project (owner, direct assignment, or group
    membership) can view it -- viewing is not gated by any specific
    permission, only by whether the project was shared with them at all.
    Specific actions on top of that (edit, delete, upload, settings, ...)
    still go through require_project_permission."""
    if project.organization_id != user.organization_id:
        raise HTTPException(404, "Project not found")
    if project.owner_id == user.id:
        return
    if not _has_explicit_project_access(db, user, project):
        raise HTTPException(403, "You do not have access to this project")


def require_project_settings_access(db: Session, user, project) -> None:
    """Project owners always manage their own project's settings/access; anyone
    else needs the `projects.settings` permission granted for this project."""
    if project.organization_id != user.organization_id:
        raise HTTPException(404, "Project not found")
    if project.owner_id == user.id:
        return
    require_project_permission(db, user, project, "projects.settings")
