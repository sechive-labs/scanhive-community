from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import group_projects, group_roles, group_users


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="groups_organization_name_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped["User | None"] = relationship()
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    users: Mapped[list["User"]] = relationship(secondary=group_users)
    roles: Mapped[list["Role"]] = relationship(secondary=group_roles)
    projects: Mapped[list["Project"]] = relationship(secondary=group_projects)
