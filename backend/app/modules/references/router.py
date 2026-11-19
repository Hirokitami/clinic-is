"""Справочники – чтение для всех вошедших пользователей."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.dependencies import current_user
from app.modules.auth.models import UserAccount
from app.modules.schedule.models import Doctor

from .models import AppointmentStatus, Cabinet, Diagnosis, ProcedureType, Service, Specialty, TestType
from .schemas import RefItem, SpecialtyOut

router = APIRouter(prefix="/api/refs", tags=["Справочники"], dependencies=[Depends(current_user)])


@router.get("/specialties", response_model=list[SpecialtyOut])
def specialties(db: Session = Depends(get_db)):
    """Специальности, по которым есть действующие врачи."""
    active = select(Doctor.specialty_code).where(Doctor.is_active.is_(True))
    return db.scalars(select(Specialty).where(Specialty.is_active.is_(True), Specialty.specialty_code.in_(active))
                      .order_by(Specialty.name)).all()


@router.get("/diagnoses", response_model=list[RefItem])
def diagnoses(db: Session = Depends(get_db)):
    return [RefItem(code=d.icd_code, name=d.name) for d in db.scalars(select(Diagnosis).order_by(Diagnosis.icd_code))]


@router.get("/procedures", response_model=list[RefItem])
def procedures(db: Session = Depends(get_db)):
    return [RefItem(code=p.procedure_code, name=p.name, extra={"minutes": p.minutes, "cabinet_no": p.cabinet_no})
            for p in db.scalars(select(ProcedureType).order_by(ProcedureType.procedure_code))]


@router.get("/services", response_model=list[RefItem])
def services(specialty: str | None = None, db: Session = Depends(get_db)):
    q = select(Service).where(Service.is_active.is_(True)).order_by(Service.service_code)
    if specialty:
        q = q.where((Service.specialty_code == specialty) | Service.specialty_code.is_(None))
    return [RefItem(code=s.service_code, name=s.name,
                    extra={"price_kzt": float(s.price_kzt), "specialty_code": s.specialty_code})
            for s in db.scalars(q)]


@router.get("/test-types", response_model=list[RefItem])
def test_types(db: Session = Depends(get_db)):
    return [RefItem(code=t.test_code, name=t.name, extra={"group": t.test_group, "ready_days": t.ready_days})
            for t in db.scalars(select(TestType).order_by(TestType.test_code))]


@router.get("/statuses", response_model=list[RefItem])
def statuses(db: Session = Depends(get_db)):
    return [RefItem(code=s.status_code, name=s.name, extra={"occupies_slot": s.occupies_slot})
            for s in db.scalars(select(AppointmentStatus))]


@router.get("/cabinets", response_model=list[RefItem])
def cabinets(db: Session = Depends(get_db), _: UserAccount = Depends(current_user)):
    return [RefItem(code=c.cabinet_no, name=c.purpose, extra={"floor_no": c.floor_no})
            for c in db.scalars(select(Cabinet).where(Cabinet.is_active.is_(True)).order_by(Cabinet.cabinet_no))]
