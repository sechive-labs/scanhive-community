from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FindingTriageHistory(Base):
    __tablename__ = "finding_triage_history"

    id: Mapped[int] = mapped_column(primary_key=True)

    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    triage_status: Mapped[str] = mapped_column(String(50), nullable=False)

    comments: Mapped[str | None] = mapped_column(String(5000), nullable=True)

    triaged_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    triaged_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    finding: Mapped["Finding"] = relationship(back_populates="triage_history")
    triaged_by: Mapped["User"] = relationship()
