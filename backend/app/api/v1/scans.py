from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import Response
from fastapi import status

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from uuid import UUID

from app.auth.dependencies import get_current_user, get_scan_uploader
from app.db.session import get_db

from app.schemas.scan import ScanType, ScanUploadResponse
from app.services.scan_service import ScanService
from app.services.project_service import ProjectService
from app.repositories.project_repository import ProjectRepository
from app.repositories.scan_repository import ScanRepository
from app.auth.project_access import require_project_permission

router = APIRouter(
    prefix="/api/v1/scans",
    tags=["Scans"]
)


@router.post(
    "/upload/{project_id}",
    response_model=ScanUploadResponse
)
def upload_scan(
    project_id: str,
    file: UploadFile = File(...),
    scan_type: ScanType = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_scan_uploader)
):
    """`project_id` accepts either the project's UUID or its (unique) name.

    A pipeline that gives a name with no matching project gets one
    auto-created (owned by the uploading user) instead of a 404 -- CI
    shouldn't need someone to click "Create project" first."""

    project_repo = ProjectRepository(db)
    try:
        project = project_repo.get_by_id(UUID(project_id))
    except ValueError:
        name = project_id.strip()
        project = project_repo.get_by_name(user.organization_id, name)
        if project is None:
            try:
                project = ProjectService(project_repo).create(name, None, user.id, user.organization_id)
            except IntegrityError:
                db.rollback()
                project = project_repo.get_by_name(user.organization_id, name)

    if project is None:
        raise HTTPException(404, "Project not found")
    require_project_permission(db, user, project, "scans.upload")

    service = ScanService(db)

    content = file.file.read()

    scan, findings = service.upload(
        project_id=project.id,
        filename=file.filename,
        content=content,
        scan_type=scan_type,
    )

    return ScanUploadResponse(
        scan_id=scan.id,
        scan_type=scan.scan_type,
        tool=scan.tool,
        filename=scan.filename,
        status=scan.status,
        findings=findings
    )


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(
    scan_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    scan = ScanRepository(db).get(scan_id)
    if scan is None:
        raise HTTPException(404, "Scan not found")

    project = ProjectRepository(db).get_by_id(scan.project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    require_project_permission(db, user, project, "scans.delete")
    ScanService(db).delete(scan)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
