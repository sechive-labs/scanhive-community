from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import Response

from sqlalchemy.orm import Session
from uuid import UUID
import re

from app.auth.dependencies import get_current_user
from app.db.session import get_db, translate_integrity_error

from app.models.user import User
from app.models.group import Group
from app.models.associations import group_projects
from app.models.project_access import ProjectAccess
from app.models.scan import Scan
from app.schemas.project_dashboard import (
    ProjectDashboardResponse,
    ProjectDetailsResponse,
)
from app.services.project_dashboard_service import ProjectDashboardService

from app.repositories.project_repository import ProjectRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectAccessResponse,
    ProjectAccessUpdate,
)
from app.services.project_service import ProjectService
from app.repositories.scan_repository import ScanRepository
from app.schemas.scan import ScanHistoryItem
from app.auth.project_access import require_project_permission, require_project_access, require_project_settings_access
from app.auth.permissions import require_permission
from app.services.project_report_service import ProjectReportService

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Projects"]
)


def report_filename(name: str, extension: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "project"
    return f"{safe}_security_report.{extension}"


def report_project(project_id: UUID, db: Session, current_user: User):
    project = ProjectRepository(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.organization_id != current_user.organization_id:
        raise HTTPException(404, "Project not found")
    require_project_permission(db, current_user, project, "projects.read")
    return project


@router.get("/{project_id}/reports/csv")
def export_project_csv(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = report_project(project_id, db, current_user)
    filename = report_filename(project.name, "csv")
    return Response(
        content=ProjectReportService(db).csv(project_id),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/reports/pdf")
def export_project_pdf(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = report_project(project_id, db, current_user)
    filename = report_filename(project.name, "pdf")
    return Response(
        content=ProjectReportService(db).pdf(project),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def report_scan(project_id: UUID, scan_id: UUID, db: Session, current_user: User):
    project = report_project(project_id, db, current_user)
    scan = db.query(Scan).filter(Scan.id == scan_id, Scan.project_id == project_id).first()
    if scan is None:
        raise HTTPException(404, "Scan not found in this project")
    return project, scan


@router.get("/{project_id}/scans/{scan_id}/reports/csv")
def export_scan_csv(
    project_id: UUID,
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project, scan = report_scan(project_id, scan_id, db, current_user)
    filename = report_filename(f"{project.name}_{scan.scan_type}_{scan.id}", "csv")
    return Response(
        content=ProjectReportService(db).csv(project_id, scan_id),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/scans/{scan_id}/reports/pdf")
def export_scan_pdf(
    project_id: UUID,
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project, scan = report_scan(project_id, scan_id, db, current_user)
    filename = report_filename(f"{project.name}_{scan.scan_type}_{scan.id}", "pdf")
    return Response(
        content=ProjectReportService(db).pdf(project, scan),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/access", response_model=ProjectAccessResponse)
def get_project_access(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectRepository(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    require_project_settings_access(db, current_user, project)
    return {
        "users": db.query(User).filter(User.id != project.owner_id, User.is_active.is_(True), User.organization_id == current_user.organization_id).order_by(User.email).all(),
        "assignments": db.query(ProjectAccess).filter(ProjectAccess.project_id == project_id).all(),
        "groups": [
            {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "member_count": len(group.users),
                "effective_role_names": sorted({role.name for role in group.roles}),
            }
            for group in db.query(Group).filter(Group.organization_id == current_user.organization_id).order_by(Group.name).all()
        ],
        "group_ids": [
            row.group_id
            for row in db.query(group_projects.c.group_id).filter(group_projects.c.project_id == project_id).all()
        ],
    }


@router.put("/{project_id}/access", response_model=ProjectAccessResponse)
def update_project_access(
    project_id: UUID,
    request: ProjectAccessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectRepository(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    require_project_settings_access(db, current_user, project)
    user_ids = {item.user_id for item in request.assignments}
    if project.owner_id in user_ids:
        raise HTTPException(400, "Project owner access cannot be reassigned")
    if db.query(User).filter(User.id.in_(user_ids), User.is_active.is_(True), User.organization_id == current_user.organization_id).count() != len(user_ids):
        raise HTTPException(400, "One or more users are invalid or disabled")
    group_ids = set(request.group_ids)
    if db.query(Group).filter(Group.id.in_(group_ids), Group.organization_id == current_user.organization_id).count() != len(group_ids):
        raise HTTPException(400, "One or more groups are invalid")
    db.query(ProjectAccess).filter(ProjectAccess.project_id == project_id).delete()
    db.add_all(ProjectAccess(project_id=project_id, user_id=item.user_id) for item in request.assignments)
    db.execute(group_projects.delete().where(group_projects.c.project_id == project_id))
    if group_ids:
        db.execute(group_projects.insert(), [{"project_id": project_id, "group_id": group_id} for group_id in group_ids])
    db.commit()
    return get_project_access(project_id, db, current_user)


@router.post(
    "",
    response_model=ProjectResponse
)
def create_project(
    request: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, "projects.create")

    repo = ProjectRepository(db)
    service = ProjectService(repo)

    with translate_integrity_error(db, "A project with this name already exists"):
        return service.create(
            request.name,
            request.description,
            current_user.id,
            current_user.organization_id,
        )


@router.get(
    "",
    response_model=list[ProjectListResponse]
)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    repo = ProjectRepository(db)
    service = ProjectService(repo)

    return service.list(current_user.id)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse
)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    repo = ProjectRepository(db)
    service = ProjectService(repo)

    project = service.get(project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    require_project_access(db, current_user, project)

    return project


@router.put(
    "/{project_id}",
    response_model=ProjectResponse
)
def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    repo = ProjectRepository(db)
    service = ProjectService(repo)

    project = service.get(project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    require_project_permission(db, current_user, project, "projects.edit")

    with translate_integrity_error(db, "A project with this name already exists"):
        return service.update(
            project,
            request.name,
            request.description,
        )


@router.delete("/{project_id}")
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    repo = ProjectRepository(db)
    service = ProjectService(repo)

    project = service.get(project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    require_project_permission(db, current_user, project, "projects.delete")

    service.delete(project)

    return {
        "message": "Project deleted successfully"
    }


@router.get(
    "/{project_id}/scans",
    response_model=list[ScanHistoryItem],
)
def get_project_scans(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = ProjectService(ProjectRepository(db)).get(project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    require_project_access(db, current_user, project)

    return ScanRepository(db).get_project_scan_history(project_id)


@router.get(
  "/{project_id}/project_details",
  response_model=ProjectDetailsResponse
)
def get_project_details(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    repo = ProjectRepository(db)
    project_service = ProjectService(repo)

    project = project_service.get(project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    require_project_access(db, current_user, project)

    dashboard_service = ProjectDashboardService(db)

    return dashboard_service.get_project_details(project_id)


@router.get(
  "/{project_id}/dashboard",
  response_model=ProjectDashboardResponse
)
def get_project_dashboard(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    repo = ProjectRepository(db)
    project_service = ProjectService(repo)

    project = project_service.get(project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    require_project_access(db, current_user, project)

    dashboard_service = ProjectDashboardService(db)

    return dashboard_service.get_project_dashboard(project_id)
