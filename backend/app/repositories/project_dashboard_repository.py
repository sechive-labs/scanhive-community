from sqlalchemy import case, func
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.finding import Finding
from app.models.project import Project
from app.models.scan import Scan
from app.repositories.result_query import latest_project_results


class ProjectDashboardRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_project(self, project_id: UUID):
        return (
            self.db.query(Project)
            .filter(Project.id == project_id)
            .first()
        )

    def get_total_scans(self, project_id: UUID) -> int:
        return (
            self.db.query(func.count(Scan.id))
            .filter(Scan.project_id == project_id)
            .scalar()
            or 0
        )

    def get_total_findings(self, project_id: UUID) -> int:
        latest_results = latest_project_results()
        return (
            self.db.query(func.count(latest_results.c.finding_id))
            .filter(latest_results.c.project_id == project_id)
            .scalar()
            or 0
        )

    def get_severity_distribution(self, project_id: UUID):
        latest_results = latest_project_results()
        return (
            self.db.query(
                func.lower(latest_results.c.severity).label("severity"),
                func.count(latest_results.c.finding_id).label("count")
            )
            .filter(latest_results.c.project_id == project_id)
            .group_by(func.lower(latest_results.c.severity))
            .all()
        )

    def get_tool_distribution(self, project_id: UUID):
        latest_results = latest_project_results()
        return (
            self.db.query(
                func.lower(latest_results.c.tool).label("tool"),
                func.count(latest_results.c.finding_id).label("count")
            )
            .filter(latest_results.c.project_id == project_id)
            .group_by(func.lower(latest_results.c.tool))
            .all()
        )

    def get_last_scan(self, project_id: UUID):
        return (
            self.db.query(
                func.max(Scan.uploaded_at)
            )
            .filter(
                Scan.project_id == project_id
            )
            .scalar()
        )

    def get_scan_trend(self, project_id: UUID):
        severity = func.lower(Finding.severity)

        return (
            self.db.query(
                Scan.id.label("scan_id"),
                Scan.tool.label("tool"),
                Scan.filename.label("filename"),
                Scan.status.label("status"),
                Scan.uploaded_at.label("uploaded_at"),

                func.count(Finding.id).label("total"),

                func.sum(
                    case(
                        (severity == "critical", 1),
                        else_=0
                    )
                ).label("critical"),

                func.sum(
                    case(
                        (severity == "high", 1),
                        else_=0
                    )
                ).label("high"),

                func.sum(
                    case(
                        (severity == "medium", 1),
                        else_=0
                    )
                ).label("medium"),

                func.sum(
                    case(
                        (severity == "low", 1),
                        else_=0
                    )
                ).label("low"),

                func.sum(
                    case(
                        (severity == "info", 1),
                        else_=0
                    )
                ).label("info")
            )
            .outerjoin(
                Finding,
                Finding.scan_id == Scan.id
            )
            .filter(
                Scan.project_id == project_id
            )
            .group_by(
                Scan.id,
                Scan.tool,
                Scan.filename,
                Scan.status,
                Scan.uploaded_at
            )
            .order_by(
                Scan.uploaded_at.asc()
            )
            .all()
        )
