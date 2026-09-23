from sqlalchemy import Boolean, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import role_includes, user_roles


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="roles_organization_name_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    permissions: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # A "Default" role (an atomic single-permission role) that ships as a
    # fixed building block -- unlike a "Composite Role" (is_system=True but
    # locked=False, e.g. "platform-admin"), which is still seeded by
    # ScanHive but can be freely edited or deleted.
    # Custom (is_system=False) roles are never locked.
    locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )

    users: Mapped[list["User"]] = relationship(
        secondary=user_roles,
        back_populates="roles",
    )

    # Composite roles: this role's permissions are its own `permissions`
    # PLUS every permission of every role it includes, recursively (e.g.
    # "platform-admin" includes "iam-admin" and "project-admin" rather than
    # duplicating their permissions directly).
    included_roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_includes,
        primaryjoin="Role.id == role_includes.c.parent_role_id",
        secondaryjoin="Role.id == role_includes.c.included_role_id",
    )

    @property
    def effective_permissions(self) -> list[str]:
        return sorted(self._collect_permissions(set()))

    def _collect_permissions(self, visited: set[int]) -> set[str]:
        if self.id is not None:
            if self.id in visited:
                return set()
            visited.add(self.id)
        permissions = set(self.permissions or [])
        for included in self.included_roles:
            permissions |= included._collect_permissions(visited)
        return permissions
