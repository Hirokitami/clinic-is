from datetime import date

from pydantic import BaseModel, Field

from .models import Doctor, ScheduleSlot


class DoctorOut(BaseModel):
    tab_no: str
    fio: str
    short_name: str
    specialty_code: str
    specialty_name: str
    cabinet_no: str
    floor_no: int
    work_phone: str | None = None
    is_active: bool


def doctor_out(d: Doctor) -> DoctorOut:
    return DoctorOut(tab_no=d.tab_no, fio=d.fio, short_name=d.short_name, specialty_code=d.specialty_code,
                     specialty_name=d.specialty.name, cabinet_no=d.cabinet_no, floor_no=d.cabinet.floor_no,
                     work_phone=d.work_phone, is_active=d.is_active)


class SlotOut(BaseModel):
    slot_id: str
    date: date
    time_start: str
    time_end: str
    cabinet_no: str
    floor_no: int
    is_busy: bool
    bookable: bool
    state: str  # free / busy / past


def slot_out(s: ScheduleSlot, bookable: bool) -> SlotOut:
    state = "busy" if s.is_busy else ("free" if bookable else "past")
    return SlotOut(slot_id=s.slot_id, date=s.slot_date, time_start=f"{s.time_start:%H:%M}",
                   time_end=f"{s.time_end:%H:%M}", cabinet_no=s.cabinet_no, floor_no=s.cabinet.floor_no,
                   is_busy=s.is_busy, bookable=bookable, state=state)


class DayScheduleOut(BaseModel):
    doctor: DoctorOut
    date: date
    works: bool
    work_days: list[int]
    slots: list[SlotOut]


class WorkRuleIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    time_start: str
    time_end: str


class WorkRulesIn(BaseModel):
    rules: list[WorkRuleIn]


class WorkRulesOut(BaseModel):
    doctor: DoctorOut
    rules: list[WorkRuleIn]
    slots_from: date | None
    slots_to: date | None


class GenerateIn(BaseModel):
    tab_no: str | None = None
    date_from: date
    date_to: date
