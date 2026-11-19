"""Подсистема «Расписание врачей»: врачи, расписание на дату, свободные интервалы (Т4),
рабочее время и формирование расписания (администратор, функция 6)."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import Forbidden
from app.modules.auth.dependencies import current_user, require_roles
from app.modules.auth.models import UserAccount

from . import service
from .models import Doctor
from .schemas import DayScheduleOut, DoctorOut, GenerateIn, WorkRulesIn, WorkRulesOut, doctor_out, slot_out

router = APIRouter(prefix="/api/schedule", tags=["Расписание врачей"])
viewers = require_roles("OPERATOR", "PATIENT", "DOCTOR", "ADMIN")
admin = require_roles("ADMIN")


@router.get("/doctors", response_model=list[DoctorOut], summary="Врачи (с отбором по специальности)")
def doctors(specialty: str | None = None, include_inactive: bool = False, db: Session = Depends(get_db),
            _: UserAccount = Depends(current_user)):
    q = select(Doctor).order_by(Doctor.last_name)
    if specialty:
        q = q.where(Doctor.specialty_code == specialty)
    if not include_inactive:
        q = q.where(Doctor.is_active.is_(True))
    return [doctor_out(d) for d in db.scalars(q)]


# ------------------------------------------------------------------ администратор
@router.get("/work-rules", response_model=list[WorkRulesOut], summary="Рабочее время врачей")
def work_rules(db: Session = Depends(get_db), _: UserAccount = Depends(admin)):
    return [service.work_rules_out(db, d) for d in db.scalars(select(Doctor).order_by(Doctor.last_name))]


@router.put("/work-rules/{tab_no}", response_model=WorkRulesOut, summary="Изменение рабочего времени врача")
def set_work_rules(tab_no: str, data: WorkRulesIn, db: Session = Depends(get_db), _: UserAccount = Depends(admin)):
    d = service.get_doctor(db, tab_no)
    service.set_work_rules(db, d, data.rules)
    return service.work_rules_out(db, d)


@router.post("/generate", summary="Формирование расписания врача на период (функция 6)")
def generate(data: GenerateIn, db: Session = Depends(get_db), _: UserAccount = Depends(admin)):
    result = service.generate_for(db, data.tab_no, data.date_from, data.date_to)
    total = sum(result.values())
    return {"created": total, "by_doctor": result,
            "message": f"Сформировано интервалов: {total}. Дни с уже существующим расписанием не изменялись."}


# ------------------------------------------------------------------ просмотр расписания
def _doctor_for(db: Session, tab_no: str, user: UserAccount) -> Doctor:
    if user.role_code == "DOCTOR" and user.tab_no != tab_no:
        raise Forbidden("Врачу доступно только собственное расписание")
    return service.get_doctor(db, tab_no)


@router.get("/{tab_no}", response_model=DayScheduleOut, summary="Расписание врача на дату: свободные и занятые интервалы")
def day(tab_no: str, on: date, db: Session = Depends(get_db), user: UserAccount = Depends(viewers)):
    d = _doctor_for(db, tab_no, user)
    slots = service.day_slots(db, tab_no, on)
    return DayScheduleOut(doctor=doctor_out(d), date=on, works=bool(slots), work_days=service.work_days(db, tab_no),
                          slots=[slot_out(s, service.is_bookable(s)) for s in slots])


@router.get("/{tab_no}/nearest", summary="Ближайшие даты со свободными интервалами (А2)")
def nearest(tab_no: str, db: Session = Depends(get_db), user: UserAccount = Depends(viewers)):
    return service.nearest_free(db, _doctor_for(db, tab_no, user))
