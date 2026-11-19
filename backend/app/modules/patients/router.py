"""Подсистема «Регистратура»: электронные карты пациентов."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.dependencies import require_roles

from . import service
from .schemas import PatientIn, PatientOut, patient_out

router = APIRouter(prefix="/api/patients", tags=["Регистратура: пациенты"],
                   dependencies=[Depends(require_roles("OPERATOR"))])


@router.get("/search", response_model=list[PatientOut],
            summary="Поиск пациента (функция 4: ИИН или ФИО + дата рождения)")
def search(iin: str | None = None, fio: str | None = None, birth_date: date | None = None,
           db: Session = Depends(get_db)):
    if iin is not None:
        return [patient_out(service.find_by_iin(db, iin))]
    return [patient_out(p) for p in service.find_by_name(db, fio, birth_date)]


@router.post("", response_model=PatientOut, status_code=201, summary="Регистрация пациента (функция 3)")
def create(data: PatientIn, db: Session = Depends(get_db)):
    return patient_out(service.register(db, data))


@router.get("/{iin}", response_model=PatientOut)
def get(iin: str, db: Session = Depends(get_db)):
    return patient_out(service.get_or_404(db, iin))


@router.put("/{iin}", response_model=PatientOut, summary="Изменение данных пациента (функция 5)")
def update(iin: str, data: PatientIn, db: Session = Depends(get_db)):
    return patient_out(service.update(db, service.get_or_404(db, iin), data))
