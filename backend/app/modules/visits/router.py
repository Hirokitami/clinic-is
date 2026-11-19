"""Подсистема «Приём пациента» – рабочее место врача-специалиста (СРО 13: окна 2–5)."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import clock
from app.core.db import get_db
from app.core.errors import Forbidden
from app.modules.appointments import service as appointments
from app.modules.appointments.schemas import AppointmentOut, appointment_out
from app.modules.auth.dependencies import require_roles
from app.modules.auth.models import UserAccount

from . import service
from .schemas import DoctorDayRow, PatientHistoryOut, VisitEditIn, VisitIn, VisitOut

router = APIRouter(prefix="/api/doctor", tags=["Приём пациента"])
doctor = require_roles("DOCTOR")


@router.get("/day", response_model=list[DoctorDayRow], summary="Пациенты на приём (функция 13, С7)")
def day(on: date | None = None, db: Session = Depends(get_db), user: UserAccount = Depends(doctor)):
    return service.doctor_day(db, user.tab_no, on or clock.today())


@router.get("/patients/{iin}/history", response_model=PatientHistoryOut, summary="История пациента (функция 14, Т9)")
def history(iin: str, db: Session = Depends(get_db), user: UserAccount = Depends(doctor)):
    if not service.doctor_can_see(db, user.tab_no, iin):
        raise Forbidden("Карта доступна только врачу, к которому пациент записан на приём")
    return service.patient_history(db, iin)


@router.get("/appointments/{appt_no}", response_model=AppointmentOut)
def appointment(appt_no: str, db: Session = Depends(get_db), user: UserAccount = Depends(doctor)):
    return appointment_out(service.own_appointment(db, appt_no, user))


@router.get("/appointments/{appt_no}/visit", response_model=VisitOut | None)
def visit_of(appt_no: str, db: Session = Depends(get_db), user: UserAccount = Depends(doctor)):
    v = service.visit_of(db, service.own_appointment(db, appt_no, user).appt_no)
    return service.visit_out(db, v) if v else None


@router.post("/appointments/{appt_no}/visit", response_model=VisitOut, status_code=201,
             summary="Фиксация результатов приёма, назначения, направления, услуги (функции 15–18)")
def create_visit(appt_no: str, data: VisitIn, db: Session = Depends(get_db), user: UserAccount = Depends(doctor)):
    v = service.save_visit(db, user, service.own_appointment(db, appt_no, user), data)
    return service.visit_out(db, v)


@router.put("/visits/{visit_no}", response_model=VisitOut, summary="Изменение результатов приёма с историей (Т10)")
def update_visit(visit_no: str, data: VisitEditIn, db: Session = Depends(get_db),
                 user: UserAccount = Depends(doctor)):
    return service.visit_out(db, service.edit_visit(db, user, service.own_visit(db, visit_no, user), data))


@router.post("/appointments/{appt_no}/no-show", response_model=AppointmentOut, summary="Отметка неявки (функция 19)")
def no_show(appt_no: str, db: Session = Depends(get_db), user: UserAccount = Depends(doctor)):
    return appointment_out(appointments.mark_no_show(db, user, service.own_appointment(db, appt_no, user)))
