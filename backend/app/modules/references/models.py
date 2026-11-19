"""Справочники ИС (СРО 10)."""
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Specialty(Base):
    __tablename__ = "ref_specialty"
    specialty_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    visit_minutes: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("visit_minutes BETWEEN 10 AND 120"),)


class Cabinet(Base):
    __tablename__ = "ref_cabinet"
    cabinet_no: Mapped[str] = mapped_column(String(10), primary_key=True)
    floor_no: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AppointmentStatus(Base):
    __tablename__ = "ref_appointment_status"
    status_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    occupies_slot: Mapped[bool] = mapped_column(Boolean)


class Diagnosis(Base):
    __tablename__ = "ref_diagnosis"
    icd_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))


class ProcedureType(Base):
    __tablename__ = "ref_procedure_type"
    procedure_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    minutes: Mapped[int] = mapped_column(Integer)
    cabinet_no: Mapped[str | None] = mapped_column(ForeignKey("ref_cabinet.cabinet_no"))


class Service(Base):
    __tablename__ = "ref_service"
    service_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    specialty_code: Mapped[str | None] = mapped_column(ForeignKey("ref_specialty.specialty_code"))
    price_kzt: Mapped[float] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("price_kzt > 0"),)


class TestType(Base):
    __tablename__ = "ref_test_type"
    test_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    test_group: Mapped[str] = mapped_column(String(30))
    ready_days: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint("test_group IN ('лабораторное', 'инструментальное')"),)
