from sqlalchemy.orm import Session

from app.models.role import Role

# Canonical, composable RBAC catalog -- mirrors the main ScanHive product's
# role catalog, with SSO removed (iam.sso.manage / "manage-sso-configuration"
# is not part of the self-hosted Community edition).
#
# The catalog has three layers, all real Role rows tied together via
# Role.included_roles (nothing here is a bare permission string floating
# outside the role system):
#   1. Atomic roles -- one per individual capability (e.g. "view-project",
#      "delete-scan"), each holding exactly one permission directly.
#   2. Mid-level composite roles ("iam-admin", "project-admin", "auditor",
#      "security-analyst") -- hold no permissions of their own, just
#      `included_roles` pointing at the atomic roles that make them up.
#   3. "platform-admin" -- a composite of composites: includes "iam-admin"
#      and "project-admin" rather than repeating their atomic roles.

ATOMIC_ROLE_TEMPLATES = [
    {"name": "manage-users", "legacy_names": ["users"], "permission": "iam.users.manage", "description": "User can have access to User Section and can perform relevant operations"},
    {"name": "user-add", "permission": "iam.users.create", "description": "User can invite and add new users"},
    {"name": "user-update", "permission": "iam.users.update", "description": "User can update existing users"},
    {"name": "user-delete", "permission": "iam.users.delete", "description": "User can remove users"},
    {"name": "manage-roles", "legacy_names": ["roles"], "permission": "iam.roles.manage", "description": "User can perform operations on roles"},
    {"name": "manage-user-groups", "legacy_names": ["user-groups"], "permission": "iam.groups.manage", "description": "User can perform operations on user groups"},
    {"name": "create-project", "permission": "projects.create", "description": "User can create new projects"},
    {"name": "edit-project", "permission": "projects.edit", "description": "User can edit project details"},
    {"name": "delete-project", "permission": "projects.delete", "description": "User can delete projects"},
    {"name": "view-project", "permission": "projects.read", "description": "User can view project details"},
    {"name": "view-scan", "permission": "scans.read", "description": "User can view scan results"},
    {"name": "upload-scan", "permission": "scans.upload", "description": "User can upload scan results"},
    {"name": "delete-scan", "permission": "scans.delete", "description": "User can delete scans"},
    {"name": "project-settings", "permission": "projects.settings", "description": "User can manage a project's settings and access"},
    {"name": "edit-results", "permission": "findings.triage", "description": "User can triage and edit finding results"},
    {"name": "analytics-dashboard", "permission": "analytics.dashboard", "description": "User can view the analytics dashboard"},
]

# name/legacy_names/description here match the spreadsheet's "Composite
# Role" column labels. `legacy_names` lets an org that already has a
# same-purpose role under an older name (from before this catalog existed)
# get renamed onto the new name in place -- same row id, so existing
# user/group assignments survive.
COMPOSITE_ROLE_TEMPLATES = [
    {
        "name": "iam-admin",
        "legacy_names": ["IAM Administrator"],
        "description": "Manages identity and access for the organization: users, roles, and user groups.",
        "includes": ["manage-users", "user-add", "user-update", "user-delete", "manage-roles", "manage-user-groups"],
    },
    {
        "name": "project-admin",
        "legacy_names": ["Project Administrator"],
        "description": "Full administrative control over projects -- create, edit, and delete projects, manage scans, configure project settings, triage findings, and view analytics.",
        "includes": [
            "create-project", "edit-project", "delete-project", "view-project",
            "view-scan", "upload-scan", "delete-scan", "project-settings", "edit-results", "analytics-dashboard",
        ],
    },
    {
        "name": "auditor",
        "legacy_names": ["Auditor"],
        "description": "Read-only visibility into projects, scans, and analytics for auditing and compliance review.",
        "includes": ["analytics-dashboard", "view-project", "view-scan"],
    },
    {
        "name": "security-analyst",
        "legacy_names": ["Security Analyst"],
        "description": "Creates and edits projects, triages findings, and reviews analytics -- without delete or project-settings/access permissions.",
        "includes": ["create-project", "edit-project", "view-project", "view-scan", "edit-results", "analytics-dashboard"],
    },
]

PLATFORM_ADMIN_NAME = "platform-admin"
PLATFORM_ADMIN_LEGACY_NAMES = ["Platform Administrator"]
PLATFORM_ADMIN_INCLUDES = ["iam-admin", "project-admin"]
PLATFORM_ADMIN_DESCRIPTION = "Full platform access -- combines every iam-admin and project-admin capability."

# Roles from an earlier, ad-hoc catalog that this one replaces outright --
# not renamed onto anything, just removed. "iam-access" was a no-op role
# (zero roles already means zero permissions), and "project-edit" is folded
# into composing a custom role from "view-project" + "project-settings"
# instead of shipping it as a default.
REMOVED_LEGACY_ROLE_NAMES = [
    "Security Administrator", "DevSecOps Engineer", "Developer", "Project Owner",
    "api-keys", "iam-access", "project-edit",
]


def _upsert_system_role(
    db: Session,
    organization_id: int,
    name: str,
    description: str,
    permissions: list[str],
    legacy_names: tuple[str, ...] = (),
    locked: bool = True,
) -> Role:
    """Create, or find-and-rename-in-place, the named system role for an organization.

    Looks up by the current canonical name first, then falls back to any
    known older name for this same role -- so renaming this catalog reuses
    the existing row (and its id, and therefore every existing user/group
    assignment) instead of creating a duplicate and orphaning the old one.
    Safe to call every startup: fully idempotent.

    `locked=True` (the default, used for every atomic role) means the role
    is a fixed building block nobody can edit or delete -- enforced in
    app/api/v1/iam.py's update_role/delete_role. Composite roles pass
    locked=False: still seeded/managed by ScanHive (is_system stays True)
    but freely editable or deletable.
    """
    role = db.query(Role).filter(Role.organization_id == organization_id, Role.name == name).first()
    if role is None:
        for legacy_name in legacy_names:
            role = db.query(Role).filter(Role.organization_id == organization_id, Role.name == legacy_name).first()
            if role is not None:
                break
    if role is None:
        role = Role(name=name, organization_id=organization_id)
        db.add(role)
    role.name = name
    role.description = description
    role.permissions = list(permissions)
    role.is_system = True
    role.locked = locked
    return role


def cleanup_legacy_roles(db: Session, organization_id: int) -> None:
    """Remove system roles from a catalog this one replaced outright."""
    db.query(Role).filter(
        Role.organization_id == organization_id,
        Role.name.in_(REMOVED_LEGACY_ROLE_NAMES),
        Role.is_system.is_(True),
    ).delete(synchronize_session=False)


def seed_default_roles(db: Session, organization_id: int) -> Role:
    """Create/update the standard role catalog for an organization.

    Returns "platform-admin", the role new organizations' first admin user
    is assigned.
    """
    atomic_roles_by_name = {
        template["name"]: _upsert_system_role(
            db, organization_id, template["name"], template["description"],
            [template["permission"]] if template["permission"] else [],
            tuple(template.get("legacy_names", ())),
        )
        for template in ATOMIC_ROLE_TEMPLATES
    }
    db.flush()

    composite_roles_by_name = {}
    for template in COMPOSITE_ROLE_TEMPLATES:
        role = _upsert_system_role(
            db, organization_id, template["name"], template["description"],
            [], tuple(template.get("legacy_names", ())), locked=False,
        )
        role.included_roles = [atomic_roles_by_name[name] for name in template["includes"]]
        composite_roles_by_name[template["name"]] = role
    db.flush()

    platform_admin = _upsert_system_role(
        db, organization_id, PLATFORM_ADMIN_NAME, PLATFORM_ADMIN_DESCRIPTION,
        [], tuple(PLATFORM_ADMIN_LEGACY_NAMES), locked=False,
    )
    platform_admin.included_roles = [
        composite_roles_by_name[name] for name in PLATFORM_ADMIN_INCLUDES
    ]
    db.flush()

    cleanup_legacy_roles(db, organization_id)

    return platform_admin
