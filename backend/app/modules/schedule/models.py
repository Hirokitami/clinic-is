from datetime import date, datetime, time

from sqlalchemy import (Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, String, Time,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.modules.references.models import Cabinet, Specialty


class Doctor(Base):
    """Врач. Идентификатор – табельный номер."""
    __tablename__ = "doctor"
    tab_no: Mapped[str] = mapped_column(String(20), primary_key=True)
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100))
    specialty_code: Mapped[str] = mapped_column(ForeignKey("ref_specialty.specialty_code"))
    cabinet_no: Mapped[str] = mapped_column(ForeignKey("ref_cabinet.cabinet_no"))
    work_phone: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    specialty: Mapped[Specialty] = relationship(lazy="joined")
    cabinet: Mapped[Cabinet] = relationship(lazy="joined")

    @property
    def fio(self) -> str:
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)

    @property
    def short_name(self) -> str:
        initials = "".join(f"{p[0]}." for p in (self.first_name, self.middle_name) if p)
        return f"{self.last_name} {initials}"


class DoctorWorkRule(Base):
    """Рабочее время врача по дням недели (0 – понедельник). Источник для формирования расписания."""
    __tablename__ = "doctor_work_rule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tab_no: Mapped[str] = mapped_column(ForeignKey("doctor.tab_no"))
    weekday: Mapped[int] = mapped_column(Integer)
    time_start: Mapped[time] = mapped_column(Time)
    time_end: Mapped[time] = mapped_column(Time)
    __table_args__ = (
        UniqueConstraint("tab_no", "weekday"),
        CheckConstraint("weekday BETWEEN 0 AND 6"),
        CheckConstraint("time_end > time_start"),
    )


class ScheduleSlot(Base):
    """Интервал расписания. Существует только в рабочее время врача."""
    __tablename__ = "schedule_slot"
    slot_id: Mapped[str] = mapped_column(String(40), primary_key=True)  # R-ГГГГММДД-табномер-NN
    tab_no: Mapped[str] = mapped_column(ForeignKey("doctor.tab_no"))
    slot_date: Mapped[date] = mapped_column(Date)
    time_start: Mapped[time] = mapped_column(Time)
    time_end: Mapped[time] = mapped_column(Time)
    cabinet_no: Mapped[str] = mapped_column(ForeignKey("ref_cabinet.cabinet_no"))
    is_busy: Mapped[bool] = mapped_column(Boolean, default=False)

    doctor: Mapped[Doctor] = relationship(lazy="joined")
    cabinet: Mapped[Cabinet] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("tab_no", "slot_date", "time_start"),
        CheckConstraint("time_end > time_start"),
        Index("ix_slot_doctor_date", "tab_no", "slot_date"),
    )

    @property
    def starts_at(self) -> datetime:
        return datetime.combine(self.slot_date, self.time_start)
