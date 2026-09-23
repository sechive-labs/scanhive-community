from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.finding import Finding
from app.models.project import Project
from app.models.scan import Scan
from app.models.project_access import ProjectAccess
from app.models.associations import group_projects, group_users
from app.repositories.result_query import latest_project_results


class ProjectRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, project: Project):

        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        return project

    def get_all(self, owner_id: int):
        latest_results = latest_project_results()

        def result_count(severity: str | None = None):
            query = select(func.count(latest_results.c.finding_id)).where(
                latest_results.c.project_id == Project.id
            )
            if severity is not None:
                query = query.where(
                    func.lower(latest_results.c.severity) == severity
                )
            return query.correlate(Project).scalar_subquery()

        last_scan = (
            select(func.max(Scan.uploaded_at))
            .where(Scan.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
        )

        scanners = (
            select(func.array_agg(func.distinct(Scan.scan_type)))
            .where(Scan.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
        )

        return (
            self.db.query(
                Project.id,
                Project.name,
                Project.description,
                Project.owner_id,
                result_count().label("total_vulnerabilities"),
                last_scan.label("last_scan"),
                scanners.label("scanners"),
                result_count("critical").label("critical"),
                result_count("high").label("high"),
                result_count("medium").label("medium"),
                result_count("low").label("low"),
                result_count("info").label("info"),
            )
            .filter(or_(
                Project.owner_id == owner_id,
                Project.id.in_(select(ProjectAccess.project_id).where(ProjectAccess.user_id == owner_id)),
                Project.id.in_(
                    select(group_projects.c.project_id)
                    .join(group_users, group_users.c.group_id == group_projects.c.group_id)
                    .where(group_users.c.user_id == owner_id)
                ),
            ))
            .all()
        )

    def get_by_id(self, project_id: UUID):

        return (
            self.db.query(Project)
            .filter(Project.id == project_id)
            .first()
        )

    def get_by_name(self, organization_id: int, name: str):

        return (
            self.db.query(Project)
            .filter(
                Project.organization_id == organization_id,
                func.lower(Project.name) == name.strip().lower(),
            )
            .first()
        )

    def delete(self, project: Project):

        self.db.delete(project)
        self.db.commit()

    def update(self):

        self.db.commit()
