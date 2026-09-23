from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy import CheckConstraint
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Uuid

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (
        CheckConstraint(
            "scan_type IN ('SAST', 'SCA', 'Secrets', "
            "'Container Security', 'IaC', 'DAST')",
            name="scans_scan_type_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

    tool: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    scan_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SAST"
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="Completed"
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )

    project: Mapped["Project"] = relationship(
        back_populates="scans"
    )

    findings: Mapped[List["Finding"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan"
    )
