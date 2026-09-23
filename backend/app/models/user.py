from __future__ import annotations

from typing import List

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import group_users, user_roles


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # NULL until the address is proven (verification link, invitation, or
    # completed password reset).
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Session tokens issued before this moment are rejected (set on password reset).
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    organization: Mapped["Organization"] = relationship(back_populates="users")

    projects: Mapped[List["Project"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    roles: Mapped[List["Role"]] = relationship(
        secondary=user_roles,
        back_populates="users",
    )
    groups: Mapped[List["Group"]] = relationship(
        secondary=group_users,
        overlaps="users",
    )
    api_keys: Mapped[List["ApiKey"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def effective_permissions(self) -> list[str]:
        group_roles = [role for group in self.groups for role in group.roles]
        return sorted({
            permission
            for role in [*self.roles, *group_roles]
            for permission in role.effective_permissions
        })

    @property
    def name(self) -> str:
        return self.email

    @property
    def effective_role_names(self) -> list[str]:
        return sorted({role.name for role in [*self.roles, *(role for group in self.groups for role in group.roles)]})

    @property
    def organization_name(self) -> str:
        return self.organization.name
