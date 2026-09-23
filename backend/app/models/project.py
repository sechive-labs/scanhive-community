from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("projects_org_name_lower_key", "organization_id", text("lower(name)"), unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    organization: Mapped["Organization"] = relationship(back_populates="projects")

    owner: Mapped["User"] = relationship(
        back_populates="projects"
    )

    scans: Mapped[List["Scan"]] = relationship(
    back_populates="project",
    cascade="all, delete-orphan"
)
