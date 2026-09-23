import csv
import io
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import DashboardRepository
from app.services.project_report_service import build_pdf


class PortfolioReportService:
    def __init__(self, db: Session):
        self.repository = DashboardRepository(db)

    def findings(self, **filters):
        return self.repository.portfolio_findings(**filters, page=1, page_size=100000)["items"]

    def csv(self, **filters) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["Result", "Severity", "Project", "Status", "Triage Status", "Scan Type", "Scanner", "File", "Scan Date"])
        for item in self.findings(**filters):
            writer.writerow([item.title, item.severity, item.project_name, item.result_status, item.triage_status, item.scan_type, item.tool, item.file_path, item.uploaded_at.isoformat()])
        return output.getvalue().encode("utf-8-sig")

    def pdf(self, **filters) -> bytes:
        findings = self.findings(**filters)
        severity = {name: 0 for name in ("critical", "high", "medium", "low", "info")}
        for item in findings:
            key = (item.severity or "info").lower()
            severity[key if key in severity else "info"] += 1
        lines = [
            ("ScanHive Portfolio Security Report", 16),
            (f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", 9),
            ("", 9), ("Executive summary", 12), (f"Total unique results: {len(findings)}", 9),
            (f"Critical: {severity['critical']}   High: {severity['high']}   Medium: {severity['medium']}   Low: {severity['low']}   Info: {severity['info']}", 9),
            ("", 9), ("Result details", 12),
        ]
        for index, item in enumerate(findings, 1):
            lines.extend([(f"{index}. [{item.severity.upper()}] {item.title}", 9), (f"   Project: {item.project_name} | Status: {item.result_status} | Triage: {item.triage_status}", 8), (f"   {item.scan_type} / {item.tool} | {item.file_path}", 8), ("", 7)])
        return build_pdf(lines)
