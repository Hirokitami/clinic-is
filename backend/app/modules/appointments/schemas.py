from datetime import date, datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.notifications.schemas import SmsOut
from app.modules.schedule.schemas import DoctorOut, doctor_out

from .models import Appointment, AppointmentHistory


class AppointmentIn(BaseModel):
    iin: str | None = None  # для пациента подставляется из учётной записи
    slot_id: str
    reason: str = ""
    confirm_existing: bool | None = None


class RescheduleIn(BaseModel):
    slot_id: str


class HistoryOut(BaseModel):
    action: str
    old_date: date | None = None
    old_time: str | None = None
    new_date: date | None = None
    new_time: str | None = None
    old_status: str | None = None
    new_status: str | None = None
    changed_at: datetime
    changed_by: str


def history_out(h: AppointmentHistory) -> HistoryOut:
    return HistoryOut(
        action=h.action, changed_at=h.changed_at, changed_by=h.changed_by,
        old_status=h.old_status, new_status=h.new_status,
        old_date=h.old_slot.slot_date if h.old_slot else None,
        old_time=f"{h.old_slot.time_start:%H:%M}" if h.old_slot else None,
        new_date=h.new_slot.slot_date if h.new_slot else None,
        new_time=f"{h.new_slot.time_start:%H:%M}" if h.new_slot else None)


class AppointmentOut(BaseModel):
    appt_no: str
    status_code: str
    status_name: str
    reason: str
    created_at: datetime
    created_by: str
    slot_id: str
    date: date
    time_start: str
    time_end: str
    cabinet_no: str
    floor_no: int
    doctor: DoctorOut
    patient_iin: str
    patient_fio: str
    patient_birth_date: date
    patient_phone: str
    history: list[HistoryOut] | None = None


def appointment_out(a: Appointment, db: Session | None = None) -> AppointmentOut:
    """С db – вместе с историей изменений."""
    s = a.slot
    hist = None
    if db is not None:
        hist = [history_out(h) for h in db.scalars(
            select(AppointmentHistory).where(AppointmentHistory.appt_no == a.appt_no).order_by(AppointmentHistory.id))]
    return AppointmentOut(
        appt_no=a.appt_no, status_code=a.status_code, status_name=a.status.name, reason=a.reason,
        created_at=a.created_at, created_by=a.created_by, slot_id=s.slot_id, date=s.slot_date,
        time_start=f"{s.time_start:%H:%M}", time_end=f"{s.time_end:%H:%M}", cabinet_no=s.cabinet_no,
        floor_no=s.cabinet.floor_no, doctor=doctor_out(s.doctor), patient_iin=a.iin, patient_fio=a.patient.fio,
        patient_birth_date=a.patient.birth_date, patient_phone=a.patient.mobile_phone, history=hist)


class AppointmentResultOut(BaseModel):
    appointment: AppointmentOut
    sms: SmsOut | None = None
    message: str
