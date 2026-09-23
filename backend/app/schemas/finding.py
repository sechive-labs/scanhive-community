from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from uuid import UUID


TriageStatus = Literal[
    "To Verify",
    "False Positive",
    "Not Exploitable",
    "Confirmed",
    "Fixed",
]

ResultStatus = Literal["New", "Recurrent"]


class TriageHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    triage_status: TriageStatus
    comments: str | None
    triaged_by: str | None = None
    triaged_at: datetime


class ProjectFindingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: UUID
    tool: str
    rule_id: str
    title: str
    severity: str
    message: str
    file_path: str
    line_number: int | None
    end_line: int | None
    start_column: int | None
    end_column: int | None
    snippet: str | None
    cwe: str | None
    owasp: str | None
    help_uri: str | None
    fingerprint: str | None
    result_status: ResultStatus
    uploaded_at: datetime
    triage_status: TriageStatus
    triage_comments: str | None
    triaged_by: str | None
    triage_history: list[TriageHistoryEntry] = []


class ProjectFindingsResponse(BaseModel):
    items: list[ProjectFindingItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class FindingTriageUpdate(BaseModel):
    triage_status: TriageStatus
    comments: str | None = Field(default=None, max_length=5000)
