from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.references.models import ProcedureType

if TYPE_CHECKING:
    from app.modules.visits.models import Visit


class Prescription(Base):
    """Назначение процедуры (Т10, Т11.1)."""
    __tablename__ = "prescription"
    rx_no: Mapped[str] = mapped_column(String(20), primary_key=True)  # N-ГГГГ-NNNNNN
    visit_no: Mapped[str] = mapped_column(ForeignKey("visit.visit_no"))
    procedure_code: Mapped[str] = mapped_column(ForeignKey("ref_procedure_type.procedure_code"))
    sessions: Mapped[int] = mapped_column(Integer)
    instructions: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    author: Mapped[str] = mapped_column(String(50))

    visit: Mapped[Visit] = relationship(lazy="joined")
    procedure: Mapped[ProcedureType] = relationship(lazy="joined")
    executions: Mapped[list[ProcedureExecution]] = relationship(
        back_populates="prescription", lazy="selectin", order_by="ProcedureExecution.executed_at")

    __table_args__ = (CheckConstraint("sessions BETWEEN 1 AND 30"),)


class ProcedureExecution(Base):
    """Выполнение процедуры (Т11.2). У назначения может быть несколько сеансов."""
    __tablename__ = "procedure_execution"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rx_no: Mapped[str] = mapped_column(ForeignKey("prescription.rx_no"))
    executed_at: Mapped[datetime] = mapped_column(DateTime)
    nurse_login: Mapped[str] = mapped_column(ForeignKey("user_account.login"))
    note: Mapped[str | None] = mapped_column(Text)

    prescription: Mapped[Prescription] = relationship(back_populates="executions")
