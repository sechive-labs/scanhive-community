from sqlalchemy import func, or_
from datetime import datetime
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.finding import Finding
from app.models.finding_triage_history import FindingTriageHistory
from app.models.scan import Scan
from app.models.user import User


class FindingRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_many(self, findings: list[Finding]) -> list[Finding]:
        self.db.add_all(findings)
        self.db.commit()

        return findings

    def classify_and_deduplicate(
        self,
        findings: list[Finding],
        project_id: UUID,
        tool: str,
        scan_type: str,
    ) -> list[Finding]:
        unique_findings = list({item.dedup_key: item for item in findings}.values())
        if not unique_findings:
            return []

        existing_keys = {
            key
            for (key,) in (
                self.db.query(Finding.dedup_key)
                .join(Scan, Scan.id == Finding.scan_id)
                .filter(
                    Scan.project_id == project_id,
                    func.lower(Scan.tool) == tool.lower(),
                    Scan.scan_type == scan_type,
                    Finding.dedup_key.in_([
                        item.dedup_key for item in unique_findings
                    ]),
                )
                .distinct()
                .all()
            )
        }

        explicit_decisions = (
            self.db.query(Finding.dedup_key, Finding.triage_status)
            .join(Scan, Scan.id == Finding.scan_id)
            .filter(
                Scan.project_id == project_id,
                func.lower(Scan.tool) == tool.lower(),
                Scan.scan_type == scan_type,
                Finding.dedup_key.in_([
                    item.dedup_key for item in unique_findings
                ]),
                Finding.triaged_by_id.is_not(None),
            )
            .order_by(
                Finding.triaged_at.desc().nullslast(),
                Finding.id.desc(),
            )
            .all()
        )

        latest_decision_by_key: dict[str, str] = {}
        for dedup_key, triage_status in explicit_decisions:
            latest_decision_by_key.setdefault(dedup_key, triage_status)

        imported_findings = []
        for item in unique_findings:
            if latest_decision_by_key.get(item.dedup_key) == "False Positive":
                continue

            item.result_status = (
                "Recurrent"
                if item.dedup_key in existing_keys
                else "New"
            )
            imported_findings.append(item)

        return imported_findings

    def get(self, finding_id: int):
        return (
            self.db.query(Finding)
            .filter(Finding.id == finding_id)
            .first()
        )

    def list_by_scan(self, scan_id: UUID):
        return (
            self.db.query(Finding)
            .filter(Finding.scan_id == scan_id)
            .all()
        )

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
    ) -> tuple[list, int]:

        query = (
            self.db.query(
                Finding.id.label("id"),
                Finding.scan_id.label("scan_id"),
                Scan.tool.label("tool"),
                Finding.rule_id.label("rule_id"),
                Finding.title.label("title"),
                Finding.severity.label("severity"),
                Finding.message.label("message"),
                Finding.file_path.label("file_path"),
                Finding.line_number.label("line_number"),
                Finding.end_line.label("end_line"),
                Finding.start_column.label("start_column"),
                Finding.end_column.label("end_column"),
                Finding.snippet.label("snippet"),
                Finding.cwe.label("cwe"),
                Finding.owasp.label("owasp"),
                Finding.help_uri.label("help_uri"),
                Finding.fingerprint.label("fingerprint"),
                Finding.result_status.label("result_status"),
                Finding.triage_status.label("triage_status"),
                Finding.triage_comments.label("triage_comments"),
                User.email.label("triaged_by"),
                Scan.uploaded_at.label("uploaded_at"),
            )
            .join(
                Scan,
                Scan.id == Finding.scan_id
            )
            .outerjoin(
                User,
                User.id == Finding.triaged_by_id,
            )
            .filter(
                Scan.project_id == project_id
            )
        )

        if severity:
            query = query.filter(
                func.lower(Finding.severity) == severity.lower()
            )

        if tool:
            query = query.filter(
                func.lower(Scan.tool) == tool.lower()
            )

        if scan_id is not None:
            query = query.filter(
                Finding.scan_id == scan_id
            )

        if search:
            search_pattern = f"%{search.strip()}%"

            query = query.filter(
                or_(
                    Finding.rule_id.ilike(search_pattern),
                    Finding.title.ilike(search_pattern),
                    Finding.message.ilike(search_pattern),
                    Finding.file_path.ilike(search_pattern),
                )
            )

        if result_status:
            query = query.filter(Finding.result_status == result_status)

        if triage_status:
            query = query.filter(Finding.triage_status == triage_status)

        total = query.count()

        offset = (page - 1) * page_size

        items = (
            query
            .order_by(
                Scan.uploaded_at.desc(),
                Finding.id.desc(),
            )
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return items, total

    def get_project_finding(
        self,
        project_id: UUID,
        finding_id: int,
    ):
        return (
            self.db.query(
                Finding.id.label("id"),
                Finding.scan_id.label("scan_id"),
                Scan.tool.label("tool"),
                Finding.rule_id.label("rule_id"),
                Finding.title.label("title"),
                Finding.severity.label("severity"),
                Finding.message.label("message"),
                Finding.file_path.label("file_path"),
                Finding.line_number.label("line_number"),
                Finding.end_line.label("end_line"),
                Finding.start_column.label("start_column"),
                Finding.end_column.label("end_column"),
                Finding.snippet.label("snippet"),
                Finding.cwe.label("cwe"),
                Finding.owasp.label("owasp"),
                Finding.help_uri.label("help_uri"),
                Finding.fingerprint.label("fingerprint"),
                Finding.result_status.label("result_status"),
                Scan.uploaded_at.label("uploaded_at"),
                Finding.triage_status.label("triage_status"),
                Finding.triage_comments.label("triage_comments"),
                User.email.label("triaged_by"),
            )
            .join(Scan, Scan.id == Finding.scan_id)
            .outerjoin(User, User.id == Finding.triaged_by_id)
            .filter(
                Scan.project_id == project_id,
                Finding.id == finding_id,
            )
            .first()
        )

    def update_triage(
        self,
        finding_id: int,
        triage_status: str,
        comments: str | None,
        triaged_by_id: int,
    ):
        """Record a new triage decision without altering any prior one.

        Each call appends an immutable `FindingTriageHistory` entry; past
        entries are never edited or removed. The Finding's own triage_status
        / triage_comments / triaged_by_id / triaged_at columns are kept in
        sync as a denormalized "current decision" for filtering and display.
        """
        finding = self.get(finding_id)
        triaged_at = datetime.utcnow()

        self.db.add(FindingTriageHistory(
            finding_id=finding_id,
            triage_status=triage_status,
            comments=comments,
            triaged_by_id=triaged_by_id,
            triaged_at=triaged_at,
        ))

        finding.triage_status = triage_status
        finding.triage_comments = comments
        finding.triaged_by_id = triaged_by_id
        finding.triaged_at = triaged_at
        self.db.commit()

    def get_triage_history(self, finding_id: int) -> list[FindingTriageHistory]:
        return (
            self.db.query(FindingTriageHistory)
            .filter(FindingTriageHistory.finding_id == finding_id)
            .order_by(
                FindingTriageHistory.triaged_at.desc(),
                FindingTriageHistory.id.desc(),
            )
            .all()
        )
