from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from uuid import UUID

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db

from app.schemas.dashboard import DashboardAnalytics, DashboardSummary, PortfolioFindingsResponse
from app.services.dashboard_service import DashboardService
from app.services.portfolio_report_service import PortfolioReportService

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"]
)


@router.get(
    "/summary",
    response_model=DashboardSummary
)
def summary(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    require_permission(user, "analytics.dashboard")
    return DashboardService(db).summary(user.organization_id)


@router.get(
    "/analytics",
    response_model=DashboardAnalytics,
)
def analytics(
    project_id: UUID | None = Query(default=None),
    tool: str | None = Query(default=None),
    scan_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_permission(user, "analytics.dashboard")
    return DashboardService(db).analytics(
        project_id=project_id,
        tool=tool,
        scan_type=scan_type,
        organization_id=user.organization_id,
    )


@router.get("/vulnerabilities", response_model=PortfolioFindingsResponse)
def vulnerabilities(
    project_id: UUID | None = Query(default=None), severity: str | None = Query(default=None),
    triage_status: str | None = Query(default=None), result_status: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200), page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db), user=Depends(get_current_user),
):
    require_permission(user, "analytics.dashboard")
    return DashboardService(db).portfolio_findings(
        organization_id=user.organization_id, project_id=project_id, severity=severity,
        triage_status=triage_status, result_status=result_status, search=search,
        page=page, page_size=page_size,
    )


@router.get("/vulnerabilities/reports/{format}")
def vulnerability_report(
    format: str, project_id: UUID | None = Query(default=None), severity: str | None = Query(default=None),
    triage_status: str | None = Query(default=None), result_status: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200), db: Session = Depends(get_db), user=Depends(get_current_user),
):
    require_permission(user, "analytics.dashboard")
    if format not in {"csv", "pdf"}:
        return Response(status_code=404)
    report = PortfolioReportService(db)
    filters = dict(organization_id=user.organization_id, project_id=project_id, severity=severity, triage_status=triage_status, result_status=result_status, search=search)
    content = report.csv(**filters) if format == "csv" else report.pdf(**filters)
    return Response(content=content, media_type="text/csv" if format == "csv" else "application/pdf", headers={"Content-Disposition": f'attachment; filename="ScanHive_portfolio_results.{format}"'})
