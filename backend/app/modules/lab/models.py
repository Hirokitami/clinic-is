from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.references.models import TestType

if TYPE_CHECKING:
    from app.modules.visits.models import Visit


class Referral(Base):
    """Направление на исследование (Т10). Результат вносит сотрудник лаборатории."""
    __tablename__ = "referral"
    ref_no: Mapped[str] = mapped_column(String(20), primary_key=True)  # D-ГГГГ-NNNNNN
    visit_no: Mapped[str] = mapped_column(ForeignKey("visit.visit_no"))
    test_code: Mapped[str] = mapped_column(ForeignKey("ref_test_type.test_code"))
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="ORDERED")  # ORDERED / DONE
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    author: Mapped[str] = mapped_column(String(50))

    visit: Mapped[Visit] = relationship(lazy="joined")
    test_type: Mapped[TestType] = relationship(lazy="joined")
    __table_args__ = (CheckConstraint("status IN ('ORDERED', 'DONE')"),)


class TestResult(Base):
    """Результат исследования (Т9, Т12)."""
    __tablename__ = "test_result"
    result_no: Mapped[str] = mapped_column(String(20), primary_key=True)  # L-ГГГГ-NNNNNN
    iin: Mapped[str] = mapped_column(ForeignKey("patient.iin"))
    test_code: Mapped[str] = mapped_column(ForeignKey("ref_test_type.test_code"))
    tab_no: Mapped[str | None] = mapped_column(ForeignKey("doctor.tab_no"))
    referral_no: Mapped[str | None] = mapped_column(ForeignKey("referral.ref_no"), unique=True)
    done_date: Mapped[date] = mapped_column(Date)
    value_text: Mapped[str] = mapped_column(Text)
    entered_by: Mapped[str | None] = mapped_column(String(50))

    test_type: Mapped[TestType] = relationship(lazy="joined")
