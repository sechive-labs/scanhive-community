from __future__ import annotations
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base
from datetime import datetime


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint(
            "triage_status IN "
            "('To Verify', 'False Positive', "
            "'Not Exploitable', 'Confirmed', 'Fixed')",
            name="findings_triage_status_check",
        ),
        CheckConstraint(
            "result_status IN ('New', 'Recurrent')",
            name="findings_result_status_check",
        ),
        UniqueConstraint(
            "scan_id",
            "dedup_key",
            name="uq_findings_scan_dedup_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    rule_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        String(5000),
        nullable=False
    )

    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False
    )

    line_number: Mapped[int] = mapped_column(
        Integer,
        nullable=True
    )

    end_line: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    start_column: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    end_column: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    snippet: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    cwe: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    owasp: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    help_uri: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    fingerprint: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )

    dedup_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    result_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="New",
    )

    triage_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="To Verify",
    )

    triage_comments: Mapped[str | None] = mapped_column(
        String(5000),
        nullable=True,
    )

    triaged_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    triaged_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    scan_id: Mapped[UUID] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE")
    )

    scan: Mapped["Scan"] = relationship(
        back_populates="findings"
    )

    triage_history: Mapped[list["FindingTriageHistory"]] = relationship(
        back_populates="finding",
        cascade="all, delete-orphan",
        order_by="FindingTriageHistory.triaged_at.desc()",
    )
