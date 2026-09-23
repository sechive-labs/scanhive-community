from sqlalchemy.orm import Session
from uuid import UUID

from app.repositories.dashboard_repository import DashboardRepository


class DashboardService:

    def __init__(self, db: Session):
        self.repo = DashboardRepository(db)

    def summary(self, organization_id: int):
        return self.repo.get_summary(organization_id)

    def analytics(
        self,
        project_id: UUID | None = None,
        tool: str | None = None,
        scan_type: str | None = None,
        organization_id: int | None = None,
    ):
        return self.repo.get_analytics(project_id, tool, scan_type, organization_id)

    def portfolio_findings(self, **filters):
        return self.repo.portfolio_findings(**filters)
