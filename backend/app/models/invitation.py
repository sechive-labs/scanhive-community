from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import invitation_roles


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization: Mapped["Organization"] = relationship()

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    invited_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invited_by: Mapped["User | None"] = relationship()

    roles: Mapped[list["Role"]] = relationship(secondary=invitation_roles)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def status(self) -> str:
        if self.accepted_at is not None:
            return "accepted"
        if self.revoked_at is not None:
            return "revoked"
        if self.expires_at <= datetime.utcnow():
            return "expired"
        return "pending"
