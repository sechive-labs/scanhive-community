from sqlalchemy import Column, ForeignKey, Integer, Table, Uuid

from app.db.base import Base


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


def association_table(name: str, left: str, right: str) -> Table:
    return Table(
        name,
        Base.metadata,
        Column(f"{left[:-1]}_id", Integer, ForeignKey(f"{left}.id", ondelete="CASCADE"), primary_key=True),
        Column(f"{right[:-1]}_id", Integer, ForeignKey(f"{right}.id", ondelete="CASCADE"), primary_key=True),
    )


group_users = association_table("group_users", "groups", "users")
group_roles = association_table("group_roles", "groups", "roles")
invitation_roles = association_table("invitation_roles", "invitations", "roles")

# Self-referential: a role can be composed of other roles (e.g. "platform-admin"
# = "iam-admin" + "project-admin") instead of duplicating every permission
# onto every admin-ish role.
role_includes = Table(
    "role_includes",
    Base.metadata,
    Column("parent_role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("included_role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)
group_projects = Table(
    "group_projects",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
)
