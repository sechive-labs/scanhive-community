from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class DashboardSummary(BaseModel):
    projects: int
    scans: int
    findings: int

    critical: int
    high: int
    medium: int
    low: int


class DashboardFilterProject(BaseModel):
    id: UUID
    name: str


class DashboardFilters(BaseModel):
    projects: list[DashboardFilterProject]
    tools: list[str]
    scan_types: list[str]


class DashboardMetric(BaseModel):
    name: str
    value: int


class DashboardBreakdown(BaseModel):
    name: str
    scans: int
    findings: int


class DashboardTrendPoint(BaseModel):
    period: str
    label: str
    scans: int
    findings: int


class DashboardAnalyticsSummary(BaseModel):
    projects: int
    scans: int
    findings: int
    critical: int
    high: int
    confirmed: int


class DashboardAnalytics(BaseModel):
    filters: DashboardFilters
    summary: DashboardAnalyticsSummary
    severity: list[DashboardMetric]
    by_project: list[DashboardBreakdown]
    by_tool: list[DashboardBreakdown]
    by_scan_type: list[DashboardBreakdown]
    trend: list[DashboardTrendPoint]


class PortfolioFindingItem(BaseModel):
    id: int
    project_id: UUID
    project_name: str
    scan_id: UUID
    title: str
    severity: str
    result_status: str
    triage_status: str
    scan_type: str
    tool: str
    file_path: str
    uploaded_at: datetime


class PortfolioFindingsResponse(BaseModel):
    items: list[PortfolioFindingItem]
    page: int
    page_size: int
    total: int
    total_pages: int
    severity: list[DashboardMetric]
    triage: list[DashboardMetric]
    status: list[DashboardMetric]
