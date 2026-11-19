from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.patients.models import Patient
from app.modules.references.models import AppointmentStatus
from app.modules.schedule.models import ScheduleSlot

# Статусы, при которых запись занимает интервал (ref_appointment_status.occupies_slot).
OCCUPYING = ("PLANNED", "DONE", "NO_SHOW")


class Appointment(Base):
    """Запись на приём (Т5, Т7). Врач, дата, время и кабинет – через интервал."""
    __tablename__ = "appointment"
    appt_no: Mapped[str] = mapped_column(String(20), primary_key=True)  # Z-ГГГГ-NNNNNN
    iin: Mapped[str] = mapped_column(ForeignKey("patient.iin"))
    slot_id: Mapped[str] = mapped_column(ForeignKey("schedule_slot.slot_id"))
    reason: Mapped[str] = mapped_column(Text)
    status_code: Mapped[str] = mapped_column(ForeignKey("ref_appointment_status.status_code"), default="PLANNED")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str] = mapped_column(ForeignKey("user_account.login"))

    patient: Mapped[Patient] = relationship(lazy="joined")
    slot: Mapped[ScheduleSlot] = relationship(lazy="joined")
    status: Mapped[AppointmentStatus] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint("trim(reason) <> ''"),
        # Защита от наложения на уровне БД: на интервал – одна запись, занимающая интервал.
        Index("ux_appointment_active_slot", "slot_id", unique=True,
              sqlite_where=text("status_code IN ('PLANNED', 'DONE', 'NO_SHOW')"),
              postgresql_where=text("status_code IN ('PLANNED', 'DONE', 'NO_SHOW')")),
        Index("ix_appointment_iin", "iin"),
    )


class AppointmentHistory(Base):
    """История изменений записи (Т7: прежние дата и время сохраняются при переносе)."""
    __tablename__ = "appointment_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appt_no: Mapped[str] = mapped_column(ForeignKey("appointment.appt_no"))
    action: Mapped[str] = mapped_column(String(50))
    old_slot_id: Mapped[str | None] = mapped_column(ForeignKey("schedule_slot.slot_id"))
    new_slot_id: Mapped[str | None] = mapped_column(ForeignKey("schedule_slot.slot_id"))
    old_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str | None] = mapped_column(String(20))
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    changed_by: Mapped[str] = mapped_column(String(50))

    old_slot: Mapped[ScheduleSlot | None] = relationship(foreign_keys=[old_slot_id], lazy="joined")
    new_slot: Mapped[ScheduleSlot | None] = relationship(foreign_keys=[new_slot_id], lazy="joined")
