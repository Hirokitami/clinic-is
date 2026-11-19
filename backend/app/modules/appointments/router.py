"""Запись на приём, перенос, отмена, подтверждение (функции 9–12, 22–23; Т5–Т8).

Оператор работает с записями любых пациентов. Пациент – только со своими (самостоятельная запись,
перенос и отмена в личном кабинете): ИИН берётся из учётной записи, чужие записи недоступны (Т13).
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ValidationFailed
from app.modules.auth.dependencies import require_roles
from app.modules.auth.models import UserAccount
from app.modules.notifications import service as sms
from app.modules.notifications.schemas import SmsOut

from . import service
from .models import Appointment
from .schemas import AppointmentIn, AppointmentOut, AppointmentResultOut, RescheduleIn, appointment_out

router = APIRouter(prefix="/api/appointments", tags=["Регистратура: записи на приём"])
booking_roles = require_roles("OPERATOR", "PATIENT")


def _result(db: Session, a: Appointment, message: str, history: bool = False) -> AppointmentResultOut:
    msg = sms.last_for(db, a.appt_no)
    return AppointmentResultOut(appointment=appointment_out(a, db if history else None),
                                sms=SmsOut.model_validate(msg) if msg else None, message=message)


@router.get("", response_model=list[AppointmentOut], summary="Список записей с отбором")
def list_(on: date | None = None, tab_no: str | None = None, iin: str | None = None, status: str | None = None,
          db: Session = Depends(get_db), _: UserAccount = Depends(require_roles("OPERATOR"))):
    return [appointment_out(a) for a in service.list_appointments(db, on, tab_no, iin, status)]


@router.post("", response_model=AppointmentResultOut, status_code=201,
             summary="Запись пациента на приём (алгоритм СРО 11, блоки 1–12)")
def create(data: AppointmentIn, db: Session = Depends(get_db), user: UserAccount = Depends(booking_roles)):
    if user.role_code == "PATIENT":
        iin = user.iin
    else:
        iin = (data.iin or "").strip()
        if not iin:
            raise ValidationFailed("Сначала найдите и подтвердите пациента", fields={"iin": "Пациент не выбран"})
    a = service.create_appointment(db, user, iin, data.slot_id, data.reason, data.confirm_existing)
    return _result(db, a, "Пациент записан" if user.role_code == "OPERATOR" else "Вы записаны на приём")


@router.get("/{appt_no}", response_model=AppointmentOut, summary="Сведения о записи (талон) с историей изменений")
def get(appt_no: str, db: Session = Depends(get_db),
        user: UserAccount = Depends(require_roles("OPERATOR", "PATIENT", "DOCTOR", "ADMIN"))):
    return appointment_out(service.load_for(db, appt_no, user), db)


@router.post("/{appt_no}/cancel", response_model=AppointmentResultOut, summary="Отмена записи (функция 11, Т6.2)")
def cancel(appt_no: str, db: Session = Depends(get_db), user: UserAccount = Depends(booking_roles)):
    a = service.cancel_appointment(db, user, service.load_for(db, appt_no, user))
    return _result(db, a, f"Запись {a.appt_no} отменена, интервал освобождён")


@router.post("/{appt_no}/reschedule", response_model=AppointmentResultOut, summary="Перенос записи (функция 10, Т6.1)")
def reschedule(appt_no: str, data: RescheduleIn, db: Session = Depends(get_db),
               user: UserAccount = Depends(booking_roles)):
    a = service.reschedule_appointment(db, user, service.load_for(db, appt_no, user), data.slot_id)
    return _result(db, a, f"Запись {a.appt_no} перенесена, прежний интервал освобождён", history=True)
