from sqlalchemy import func, select

from app.models.finding import Finding
from app.models.scan import Scan


def latest_project_results():
    ranked = (
        select(
            Finding.id.label("finding_id"),
            Scan.project_id.label("project_id"),
            Scan.tool.label("tool"),
            Scan.scan_type.label("scan_type"),
            Finding.dedup_key.label("dedup_key"),
            Finding.severity.label("severity"),
            Finding.triage_status.label("triage_status"),
            func.row_number().over(
                partition_by=(
                    Scan.project_id,
                    func.lower(Scan.tool),
                    Scan.scan_type,
                    Finding.dedup_key,
                ),
                order_by=(Scan.uploaded_at.desc(), Finding.id.desc()),
            ).label("occurrence_number"),
        )
        .join(Scan, Scan.id == Finding.scan_id)
        .subquery()
    )

    return (
        select(
            ranked.c.finding_id,
            ranked.c.project_id,
            ranked.c.tool,
            ranked.c.scan_type,
            ranked.c.dedup_key,
            ranked.c.severity,
            ranked.c.triage_status,
        )
        .where(ranked.c.occurrence_number == 1)
        .subquery()
    )
