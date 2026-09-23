from fastapi import HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.repositories.project_dashboard_repository import (
    ProjectDashboardRepository,
)


class ProjectDashboardService:

    def __init__(self, db: Session):
        self.repository = ProjectDashboardRepository(db)

    def get_project_details(self, project_id: UUID) -> dict:

        project = self.repository.get_project(project_id)

        if project is None:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        severity = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }

        severity_rows = (
            self.repository
            .get_severity_distribution(project_id)
        )

        for row in severity_rows:

            normalized_severity = (
                row.severity or "info"
            ).lower()

            count = int(row.count or 0)

            if normalized_severity in severity:
                severity[normalized_severity] = count
            else:
                severity["info"] += count

        tools = {}

        tool_rows = (
            self.repository
            .get_tool_distribution(project_id)
        )

        for row in tool_rows:

            tool_name = (
                row.tool or "unknown"
            ).lower()

            tools[tool_name] = int(row.count or 0)

        return {
            "project_id": project.id,
            "project_name": project.name,
            "total_scans": (
                self.repository
                .get_total_scans(project_id)
            ),
            "total_findings": (
                self.repository
                .get_total_findings(project_id)
            ),
            "severity": severity,
            "tools": tools,
            "last_scan": (
                self.repository
                .get_last_scan(project_id)
            )
        }

    def get_project_dashboard(self, project_id: UUID) -> dict:

        dashboard = self.get_project_details(project_id)
        trend = []

        trend_rows = (
            self.repository
            .get_scan_trend(project_id)
        )

        for row in trend_rows:
            trend.append(
                {
                    "scan_id": row.scan_id,
                    "tool": row.tool or "unknown",
                    "filename": row.filename,
                    "status": row.status,
                    "uploaded_at": row.uploaded_at,
                    "total": int(row.total or 0),
                    "critical": int(row.critical or 0),
                    "high": int(row.high or 0),
                    "medium": int(row.medium or 0),
                    "low": int(row.low or 0),
                    "info": int(row.info or 0)
                }
            )

        dashboard["trend"] = trend

        return dashboard
