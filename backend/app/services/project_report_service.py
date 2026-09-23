import csv
import io
import textwrap
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session
from app.models.finding import Finding
from app.models.project import Project
from app.models.scan import Scan
from app.repositories.result_query import latest_project_results


class ProjectReportService:
    def __init__(self, db: Session):
        self.db = db

    def findings(self, project_id: UUID, scan_id: UUID | None = None):
        latest_results = latest_project_results()
        query = (
            self.db.query(
                Finding.title, Finding.severity, Finding.result_status, Finding.triage_status,
                Scan.scan_type, Scan.tool, Finding.rule_id, Finding.file_path,
                Finding.line_number, Finding.message, Scan.uploaded_at,
            )
            .join(Scan, Scan.id == Finding.scan_id)
            .filter(Scan.project_id == project_id)
        )
        if scan_id is not None:
            query = query.filter(Scan.id == scan_id)
        else:
            query = query.join(
                latest_results,
                latest_results.c.finding_id == Finding.id,
            )
        return query.order_by(Scan.uploaded_at.desc(), Finding.id.desc()).all()

    def csv(self, project_id: UUID, scan_id: UUID | None = None) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["Result", "Severity", "Status", "Triage Status", "Scan Type", "Scanner", "Rule ID", "File", "Line", "Message", "Scan Date"])
        for item in self.findings(project_id, scan_id):
            writer.writerow([
                item.title, item.severity, item.result_status, item.triage_status, item.scan_type,
                item.tool, item.rule_id, item.file_path, item.line_number or "",
                item.message, item.uploaded_at.isoformat() if item.uploaded_at else "",
            ])
        return output.getvalue().encode("utf-8-sig")

    def pdf(self, project: Project, scan: Scan | None = None) -> bytes:
        findings = self.findings(project.id, scan.id if scan else None)
        severity = {name: 0 for name in ("critical", "high", "medium", "low", "info")}
        tools: set[str] = set()
        for item in findings:
            key = (item.severity or "info").lower()
            severity[key if key in severity else "info"] += 1
            tools.add(item.tool)

        lines = [
            ("ScanHive Scan Security Report" if scan else "ScanHive Project Security Report", 16),
            (project.name, 13),
            (f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", 9),
            ("", 9),
            *(([(f"Scan: {scan.scan_type} / {scan.tool}", 9), (f"Source: {scan.filename}", 8), ("", 8)]) if scan else []),
            ("Executive summary", 12),
            (f"Total results: {len(findings)}", 9),
            (f"Critical: {severity['critical']}   High: {severity['high']}   Medium: {severity['medium']}   Low: {severity['low']}   Info: {severity['info']}", 9),
            (f"Scanners: {', '.join(sorted(tools)) or 'None'}", 9),
            ("", 9),
            ("Result details", 12),
        ]
        for index, item in enumerate(findings, 1):
            location = item.file_path or "No location"
            if item.line_number:
                location += f":{item.line_number}"
            lines.append((f"{index}. [{item.severity.upper()}] {item.title}", 9))
            lines.append((f"   Status: {item.result_status} | Triage Status: {item.triage_status} | {item.scan_type} / {item.tool} | Rule: {item.rule_id}", 8))
            lines.append((f"   Location: {location}", 8))
            for wrapped in textwrap.wrap(item.message or "", width=105)[:3]:
                lines.append((f"   {wrapped}", 8))
            lines.append(("", 7))
        return build_pdf(lines)


def build_pdf(lines: list[tuple[str, int]]) -> bytes:
    pages: list[list[tuple[str, int]]] = [[]]
    used = 0
    for line in lines:
        height = max(line[1] + 4, 12)
        if used + height > 730:
            pages.append([])
            used = 0
        pages[-1].append(line)
        used += height

    objects: list[bytes] = [b"", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_ids = []
    for page_number, page in enumerate(pages, 1):
        commands = ["BT", "/F1 9 Tf", "40 800 Td"]
        current_size = 9
        for value, size in page:
            if size != current_size:
                commands.append(f"/F1 {size} Tf")
                current_size = size
            safe = value.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.extend([f"({safe}) Tj", f"0 -{max(size + 4, 12)} Td"])
        commands.extend(["/F1 8 Tf", f"0 -10 Td", f"(Page {page_number} of {len(pages)}) Tj", "ET"])
        stream = "\n".join(commands).encode("latin-1")
        content_id = len(objects) + 1
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
        page_id = len(objects) + 1
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode())
        page_ids.append(page_id)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{item} 0 R' for item in page_ids)}] /Count {len(page_ids)} >>".encode()

    result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(result)
