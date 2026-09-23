from fastapi import HTTPException

# Atomic permission strings, grouped the way ScanHive's own RBAC documents
# them. Community edition intentionally excludes iam.sso.manage -- SSO is
# not part of this edition.
PERMISSION_CATALOG: dict[str, str] = {
    "iam.users.manage": "Full user management: list, invite, edit, delete users, and view IAM roles",
    "iam.users.create": "Invite new users",
    "iam.users.update": "Edit existing users (name, roles, active status)",
    "iam.users.delete": "Remove users",
    "iam.roles.manage": "Create, edit, and delete custom roles",
    "iam.groups.manage": "Create, edit, and delete user groups and their project assignments",
    "projects.create": "Create a new project",
    "projects.edit": "Edit a project's name and description",
    "projects.delete": "Delete a project",
    "projects.read": "Export a project's report as PDF/CSV",
    "scans.read": "View scans (reserved for future standalone gating)",
    "scans.upload": "Upload a SARIF scan result to a project",
    "scans.delete": "Delete a scan from a project",
    "projects.settings": "Manage a project's access list (users and groups)",
    "findings.triage": "Triage findings (Confirmed / False Positive / Fixed / etc.)",
    "analytics.dashboard": "View the portfolio-wide analytics dashboard",
}


def user_has_permission(user, *permissions: str) -> bool:
    effective = set(user.effective_permissions)
    return any(permission in effective for permission in permissions)


def require_permission(user, *permissions: str) -> None:
    if not user_has_permission(user, *permissions):
        raise HTTPException(
            status_code=403,
            detail=f"Permission required: {' or '.join(permissions)}",
        )
