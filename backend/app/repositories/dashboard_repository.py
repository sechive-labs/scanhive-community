from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.scan import Scan
from app.models.finding import Finding
from app.repositories.result_query import latest_project_results


class DashboardRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_summary(self, organization_id: int):

        projects = self.db.query(func.count(Project.id)).filter(Project.organization_id == organization_id).scalar()

        scans = self.db.query(func.count(Scan.id)).join(Project, Project.id == Scan.project_id).filter(Project.organization_id == organization_id).scalar()

        latest_results = latest_project_results()
        organization_projects = self.db.query(Project.id).filter(Project.organization_id == organization_id)
        findings = self.db.query(func.count(latest_results.c.finding_id)).filter(latest_results.c.project_id.in_(organization_projects)).scalar()

        critical = (
            self.db.query(func.count(latest_results.c.finding_id))
            .filter(latest_results.c.project_id.in_(organization_projects), func.lower(latest_results.c.severity) == "critical")
            .scalar()
        )

        high = (
            self.db.query(func.count(latest_results.c.finding_id))
            .filter(latest_results.c.project_id.in_(organization_projects), func.lower(latest_results.c.severity) == "high")
            .scalar()
        )

        medium = (
            self.db.query(func.count(latest_results.c.finding_id))
            .filter(latest_results.c.project_id.in_(organization_projects), func.lower(latest_results.c.severity) == "medium")
            .scalar()
        )

        low = (
            self.db.query(func.count(latest_results.c.finding_id))
            .filter(latest_results.c.project_id.in_(organization_projects), func.lower(latest_results.c.severity) == "low")
            .scalar()
        )

        return {
            "projects": projects,
            "scans": scans,
            "findings": findings,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        }

    def get_analytics(self, project_id=None, tool=None, scan_type=None, organization_id=None):
        scan_query = self.db.query(Scan).join(Project, Project.id == Scan.project_id)
        if organization_id is not None:
            scan_query = scan_query.filter(Project.organization_id == organization_id)
        if project_id is not None:
            scan_query = scan_query.filter(Scan.project_id == project_id)
        if tool:
            scan_query = scan_query.filter(Scan.tool == tool)
        if scan_type:
            scan_query = scan_query.filter(Scan.scan_type == scan_type)

        scans = scan_query.all()
        scan_ids = [scan.id for scan in scans]
        finding_rows = []
        if scan_ids:
            finding_rows = (
                self.db.query(
                    Finding.severity,
                    Finding.triage_status,
                    Finding.scan_id,
                    Finding.result_status,
                )
                .filter(Finding.scan_id.in_(scan_ids))
                .all()
            )

        projects_query = self.db.query(Project)
        if organization_id is not None:
            projects_query = projects_query.filter(Project.organization_id == organization_id)
        projects = projects_query.order_by(Project.name.asc()).all()
        project_names = {project.id: project.name for project in projects}
        scan_findings = {scan_id: 0 for scan_id in scan_ids}
        latest_results = latest_project_results()
        unique_query = self.db.query(latest_results)
        if organization_id is not None:
            unique_query = unique_query.filter(latest_results.c.project_id.in_([project.id for project in projects]))
        if project_id is not None:
            unique_query = unique_query.filter(latest_results.c.project_id == project_id)
        if tool:
            unique_query = unique_query.filter(latest_results.c.tool == tool)
        if scan_type:
            unique_query = unique_query.filter(latest_results.c.scan_type == scan_type)
        unique_rows = unique_query.all()

        severity_counts = {name: 0 for name in ("critical", "high", "medium", "low", "info")}
        confirmed = 0
        for row in unique_rows:
            severity = row.severity
            triage_status = row.triage_status
            normalized = (severity or "info").lower()
            severity_counts[normalized if normalized in severity_counts else "info"] += 1
            if triage_status == "Confirmed":
                confirmed += 1

        for _severity, _triage_status, finding_scan_id, result_status in finding_rows:
            if result_status == "New":
                scan_findings[finding_scan_id] += 1

        def breakdown(key_fn, name_fn, result_key_fn):
            values = {}
            for scan in scans:
                key = key_fn(scan)
                if key not in values:
                    values[key] = {"name": name_fn(scan), "scans": 0, "findings": 0}
                values[key]["scans"] += 1
            for result in unique_rows:
                key = result_key_fn(result)
                if key in values:
                    values[key]["findings"] += 1
            return sorted(values.values(), key=lambda item: (-item["findings"], item["name"]))

        now = datetime.utcnow()
        periods = []
        for offset in range(5, -1, -1):
            month_index = now.year * 12 + now.month - 1 - offset
            year, zero_month = divmod(month_index, 12)
            month = zero_month + 1
            periods.append((f"{year:04d}-{month:02d}", datetime(year, month, 1).strftime("%b")))
        trend = {period: {"period": period, "label": label, "scans": 0, "findings": 0} for period, label in periods}
        for scan in scans:
            period = scan.uploaded_at.strftime("%Y-%m")
            if period in trend:
                trend[period]["scans"] += 1
                trend[period]["findings"] += scan_findings[scan.id]

        filtered_project_count = len({scan.project_id for scan in scans})
        if project_id is None and not tool and not scan_type:
            filtered_project_count = len(projects)

        return {
            "filters": {
                "projects": [{"id": project.id, "name": project.name} for project in projects],
                "tools": sorted({scan.tool for scan in scans}),
                "scan_types": sorted({scan.scan_type for scan in scans}),
            },
            "summary": {
                "projects": filtered_project_count,
                "scans": len(scans),
                "findings": len(unique_rows),
                "critical": severity_counts["critical"],
                "high": severity_counts["high"],
                "confirmed": confirmed,
            },
            "severity": [{"name": name.title(), "value": severity_counts[name]} for name in severity_counts],
            "by_project": breakdown(lambda scan: scan.project_id, lambda scan: project_names.get(scan.project_id, "Unknown"), lambda result: result.project_id)[:8],
            "by_tool": breakdown(lambda scan: scan.tool, lambda scan: scan.tool, lambda result: result.tool),
            "by_scan_type": breakdown(lambda scan: scan.scan_type, lambda scan: scan.scan_type, lambda result: result.scan_type),
            "trend": list(trend.values()),
        }

    def portfolio_findings(self, organization_id, project_id=None, severity=None, triage_status=None, result_status=None, search=None, page=1, page_size=25):
        latest_results = latest_project_results()
        query = (
            self.db.query(
                Finding.id,
                Project.id.label("project_id"),
                Project.name.label("project_name"),
                Scan.id.label("scan_id"),
                Finding.title,
                Finding.severity,
                Finding.result_status,
                Finding.triage_status,
                Scan.scan_type,
                Scan.tool,
                Finding.file_path,
                Scan.uploaded_at,
            )
            .join(latest_results, latest_results.c.finding_id == Finding.id)
            .join(Scan, Scan.id == Finding.scan_id)
            .join(Project, Project.id == Scan.project_id)
            .filter(Project.organization_id == organization_id)
        )
        if project_id is not None:
            query = query.filter(Project.id == project_id)
        if severity:
            query = query.filter(func.lower(Finding.severity) == severity.lower())
        if triage_status:
            query = query.filter(Finding.triage_status == triage_status)
        if result_status:
            query = query.filter(Finding.result_status == result_status)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(Finding.title.ilike(pattern), Finding.rule_id.ilike(pattern), Finding.file_path.ilike(pattern)))
        total = query.count()
        severity_rows = query.with_entities(Finding.severity, func.count(Finding.id)).group_by(Finding.severity).all()
        triage_rows = query.with_entities(Finding.triage_status, func.count(Finding.id)).group_by(Finding.triage_status).all()
        status_rows = query.with_entities(Finding.result_status, func.count(Finding.id)).group_by(Finding.result_status).all()
        items = query.order_by(Scan.uploaded_at.desc(), Finding.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": items, "page": page, "page_size": page_size, "total": total,
            "total_pages": max((total + page_size - 1) // page_size, 1),
            "severity": [{"name": name.title(), "value": count} for name, count in severity_rows],
            "triage": [{"name": name, "value": count} for name, count in triage_rows],
            "status": [{"name": name, "value": count} for name, count in status_rows],
        }
