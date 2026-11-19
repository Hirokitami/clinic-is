from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.appointments.models import Appointment
from app.modules.references.models import Diagnosis, Service


class Visit(Base):
    """Приём (посещение): результаты приёма (Т10)."""
    __tablename__ = "visit"
    visit_no: Mapped[str] = mapped_column(String(20), primary_key=True)  # P-ГГГГ-NNNNNN
    appt_no: Mapped[str] = mapped_column(ForeignKey("appointment.appt_no"), unique=True)
    complaints: Mapped[str] = mapped_column(Text)
    icd_code: Mapped[str] = mapped_column(ForeignKey("ref_diagnosis.icd_code"))
    conclusion: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    author: Mapped[str] = mapped_column(String(50))

    appointment: Mapped[Appointment] = relationship(lazy="joined")
    diagnosis: Mapped[Diagnosis] = relationship(lazy="joined")


class VisitChange(Base):
    """История изменений результатов приёма (Т10): прежнее и новое значение, автор и дата."""
    __tablename__ = "visit_change"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_no: Mapped[str] = mapped_column(ForeignKey("visit.visit_no"))
    field: Mapped[str] = mapped_column(String(30))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    changed_by: Mapped[str] = mapped_column(String(50))


class RenderedService(Base):
    """Оказанная услуга: цена фиксируется на дату оказания."""
    __tablename__ = "rendered_service"
    line_no: Mapped[str] = mapped_column(String(20), primary_key=True)  # U-ГГГГ-NNNNNN
    visit_no: Mapped[str] = mapped_column(ForeignKey("visit.visit_no"))
    service_code: Mapped[str] = mapped_column(ForeignKey("ref_service.service_code"))
    qty: Mapped[int] = mapped_column(Integer, default=1)
    price_kzt: Mapped[float] = mapped_column(Numeric(12, 2))

    service: Mapped[Service] = relationship(lazy="joined")
    visit: Mapped[Visit] = relationship(lazy="joined")
    __table_args__ = (CheckConstraint("qty > 0"),)
