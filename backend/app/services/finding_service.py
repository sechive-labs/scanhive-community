from math import ceil

from sqlalchemy.orm import Session

from app.repositories.finding_repository import FindingRepository
from uuid import UUID


class FindingService:

    ALLOWED_SEVERITIES = {
        "critical",
        "high",
        "medium",
        "low",
        "info",
    }
    ALLOWED_RESULT_STATUSES = {"New", "Recurrent"}
    ALLOWED_TRIAGE_STATUSES = {
        "To Verify",
        "False Positive",
        "Not Exploitable",
        "Confirmed",
        "Fixed",
    }

    def __init__(self, db: Session):
        self.repository = FindingRepository(db)

    def get_project_findings(
        self,
        project_id: UUID,
        severity: str | None = None,
        tool: str | None = None,
        scan_id: UUID | None = None,
        search: str | None = None,
        result_status: str | None = None,
        triage_status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:

        normalized_severity = None

        if severity:
            normalized_severity = severity.strip().lower()

            if normalized_severity not in self.ALLOWED_SEVERITIES:
                raise ValueError(
                    "Severity must be one of: "
                    "critical, high, medium, low, info"
                )

        normalized_tool = None

        if tool:
            normalized_tool = tool.strip()

        normalized_search = None

        if search and search.strip():
            normalized_search = search.strip()

        normalized_result_status = result_status.strip() if result_status else None
        if normalized_result_status not in self.ALLOWED_RESULT_STATUSES and normalized_result_status is not None:
            raise ValueError("Status must be one of: New, Recurrent")

        normalized_triage_status = triage_status.strip() if triage_status else None
        if normalized_triage_status not in self.ALLOWED_TRIAGE_STATUSES and normalized_triage_status is not None:
            raise ValueError(
                "Triage status must be one of: To Verify, False Positive, Not Exploitable, Confirmed, Fixed"
            )

        items, total = self.repository.get_project_findings(
            project_id=project_id,
            severity=normalized_severity,
            tool=normalized_tool,
            scan_id=scan_id,
            search=normalized_search,
            result_status=normalized_result_status,
            triage_status=normalized_triage_status,
            page=page,
            page_size=page_size,
        )

        total_pages = (
            ceil(total / page_size)
            if total > 0
            else 0
        )

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }
