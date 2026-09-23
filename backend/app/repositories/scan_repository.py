from sqlalchemy.orm import Session
from uuid import UUID

from app.models.scan import Scan
from app.models.finding import Finding
from sqlalchemy import func


class ScanRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, scan: Scan):

        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)

        return scan

    def get(self, scan_id: UUID):

        return (
            self.db.query(Scan)
            .filter(Scan.id == scan_id)
            .first()
        )

    def delete(self, scan: Scan) -> None:
        self.db.delete(scan)
        self.db.commit()

    def list_by_project(self, project_id: UUID):

        return (
            self.db.query(Scan)
            .filter(Scan.project_id == project_id)
            .all()
        )

    def get_project_scan_history(self, project_id: UUID):

        return (
            self.db.query(
                Scan.id.label("id"),
                Scan.scan_type.label("scan_type"),
                Scan.tool.label("tool"),
                Scan.filename.label("filename"),
                Scan.status.label("status"),
                Scan.uploaded_at.label("uploaded_at"),
                func.count(Finding.id).label("findings"),
            )
            .outerjoin(Finding, Finding.scan_id == Scan.id)
            .filter(Scan.project_id == project_id)
            .group_by(
                Scan.id,
                Scan.scan_type,
                Scan.tool,
                Scan.filename,
                Scan.status,
                Scan.uploaded_at,
            )
            .order_by(Scan.uploaded_at.desc())
            .all()
        )
