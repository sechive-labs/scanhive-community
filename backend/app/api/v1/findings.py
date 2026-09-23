from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query

from sqlalchemy.orm import Session
from uuid import UUID

from app.auth.dependencies import get_current_user
from app.db.session import get_db

from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.finding import (
    FindingTriageUpdate,
    ProjectFindingItem,
    ProjectFindingsResponse,
    TriageHistoryEntry,
)
from app.services.finding_service import FindingService
from app.services.project_service import ProjectService
from app.auth.project_access import require_project_permission, require_project_access


router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Findings"],
)


def verify_project_access(
    project_id: UUID,
    db: Session,
    current_user: User,
):
    project = ProjectService(ProjectRepository(db)).get(project_id)

    if project is None:
        raise HTTPException(404, "Project not found")

    require_project_access(db, current_user, project)

    return project


def with_triage_history(finding_row, service: FindingService) -> dict:
    history = service.repository.get_triage_history(finding_row.id)
    return {
        **finding_row._mapping,
        "triage_history": [
            TriageHistoryEntry(
                id=entry.id,
                triage_status=entry.triage_status,
                comments=entry.comments,
                triaged_by=entry.triaged_by.email if entry.triaged_by else None,
                triaged_at=entry.triaged_at,
            )
            for entry in history
        ],
    }


@router.get(
    "/{project_id}/findings",
    response_model=ProjectFindingsResponse,
)
def get_project_findings(
    project_id: UUID,
    severity: str | None = Query(default=None),
    tool: str | None = Query(default=None),
    scan_id: UUID | None = Query(default=None),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
    ),
    result_status: str | None = Query(default=None),
    triage_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    verify_project_access(project_id, db, current_user)

    service = FindingService(db)

    try:
        return service.get_project_findings(
            project_id=project_id,
            severity=severity,
            tool=tool,
            scan_id=scan_id,
            search=search,
            result_status=result_status,
            triage_status=triage_status,
            page=page,
            page_size=page_size,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.get(
    "/{project_id}/findings/{finding_id}",
    response_model=ProjectFindingItem,
)
def get_finding_details(
    project_id: UUID,
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_project_access(project_id, db, current_user)
    service = FindingService(db)
    finding = service.repository.get_project_finding(
        project_id,
        finding_id,
    )

    if finding is None:
        raise HTTPException(404, "Finding not found")

    return with_triage_history(finding, service)


@router.put(
    "/{project_id}/findings/{finding_id}/triage",
    response_model=ProjectFindingItem,
)
def update_finding_triage(
    project_id: UUID,
    finding_id: int,
    request: FindingTriageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_project_access(project_id, db, current_user)
    project = ProjectService(ProjectRepository(db)).get(project_id)
    require_project_permission(db, current_user, project, "findings.triage")
    service = FindingService(db)
    finding = service.repository.get_project_finding(
        project_id,
        finding_id,
    )

    if finding is None:
        raise HTTPException(404, "Finding not found")

    comments = request.comments.strip() if request.comments else None
    service.repository.update_triage(
        finding_id,
        request.triage_status,
        comments,
        current_user.id,
    )

    updated = service.repository.get_project_finding(
        project_id,
        finding_id,
    )
    return with_triage_history(updated, service)
