"""Подсистема «Личный кабинет пациента» (функции 22–24, Т12).

Запись, перенос и отмена – общие функции модуля appointments (в пределах роли пациента).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.appointments.schemas import AppointmentOut, appointment_out
from app.modules.appointments.service import list_appointments
from app.modules.auth.dependencies import require_roles
from app.modules.auth.models import UserAccount
from app.modules.visits.schemas import PatientHistoryOut
from app.modules.visits.service import patient_history

router = APIRouter(prefix="/api/cabinet", tags=["Личный кабинет пациента"])


class CabinetOut(BaseModel):
    appointments: list[AppointmentOut]
    health: PatientHistoryOut


@router.get("", response_model=CabinetOut, summary="Свои записи и сведения о здоровье")
def cabinet(db: Session = Depends(get_db), user: UserAccount = Depends(require_roles("PATIENT"))):
    return CabinetOut(appointments=[appointment_out(a) for a in list_appointments(db, iin=user.iin)],
                      health=patient_history(db, user.iin))
