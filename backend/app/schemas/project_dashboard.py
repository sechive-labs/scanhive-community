from datetime import datetime

from pydantic import BaseModel
from uuid import UUID


class SeveritySummary(BaseModel):
    critical: int
    high: int
    medium: int
    low: int
    info: int


class ScanTrendItem(BaseModel):
    scan_id: UUID
    tool: str
    filename: str
    status: str
    uploaded_at: datetime
    total: int
    critical: int
    high: int
    medium: int
    low: int
    info: int


class ProjectDetailsResponse(BaseModel):
    project_id: UUID
    project_name: str
    total_scans: int
    total_findings: int
    severity: SeveritySummary
    tools: dict[str, int]
    last_scan: datetime | None


class ProjectDashboardResponse(ProjectDetailsResponse):
    trend: list[ScanTrendItem]
