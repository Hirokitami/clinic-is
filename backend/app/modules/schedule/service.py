"""Подсистема «Расписание врачей» (функции 6–8): формирование, просмотр, поиск свободных интервалов."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import NotFound, ValidationFailed

from .models import Doctor, DoctorWorkRule, ScheduleSlot
from .schemas import WorkRuleIn, WorkRulesOut, doctor_out


def is_bookable(slot: ScheduleSlot) -> bool:
    """Интервал можно выбрать: свободен, врач принимает, время ещё не наступило."""
    return (not slot.is_busy) and slot.doctor.is_active and slot.starts_at > clock.now()


def get_doctor(db: Session, tab_no: str) -> Doctor:
    d = db.get(Doctor, tab_no)
    if not d:
        raise NotFound("Врач не найден")
    return d


def slot_id_for(tab_no: str, d: date, n: int) -> str:
    return f"R-{d:%Y%m%d}-{tab_no.replace('-', '')}-{n:02d}"


def day_slots(db: Session, tab_no: str, on: date) -> list[ScheduleSlot]:
    return list(db.scalars(select(ScheduleSlot).where(ScheduleSlot.tab_no == tab_no, ScheduleSlot.slot_date == on)
                           .order_by(ScheduleSlot.time_start)))


def work_days(db: Session, tab_no: str) -> list[int]:
    return sorted(db.scalars(select(DoctorWorkRule.weekday).where(DoctorWorkRule.tab_no == tab_no)))


def generate(db: Session, doctor: Doctor, date_from: date, date_to: date) -> int:
    """Формирование расписания: нарезка рабочего времени на интервалы длительностью приёма специальности.

    Дни, на которые у врача уже есть интервалы, не изменяются (существующие записи не затрагиваются).
    Возвращает число созданных интервалов.
    """
    rules = {r.weekday: r for r in db.scalars(select(DoctorWorkRule).where(DoctorWorkRule.tab_no == doctor.tab_no))}
    step = timedelta(minutes=doctor.specialty.visit_minutes)
    existing_days = set(db.scalars(
        select(ScheduleSlot.slot_date).where(ScheduleSlot.tab_no == doctor.tab_no,
                                             ScheduleSlot.slot_date.between(date_from, date_to)).distinct()))
    created = 0
    d = date_from
    while d <= date_to:
        rule = rules.get(d.weekday())
        if rule and d not in existing_days:
            cur = datetime.combine(d, rule.time_start)
            end = datetime.combine(d, rule.time_end)
            n = 1
            while cur + step <= end:
                db.add(ScheduleSlot(slot_id=slot_id_for(doctor.tab_no, d, n), tab_no=doctor.tab_no, slot_date=d,
                                    time_start=cur.time(), time_end=(cur + step).time(),
                                    cabinet_no=doctor.cabinet_no, is_busy=False))
                cur += step
                n += 1
                created += 1
        d += timedelta(days=1)
    return created


def generate_for(db: Session, tab_no: str | None, date_from: date, date_to: date) -> dict[str, int]:
    if date_to < date_from:
        raise ValidationFailed("Дата окончания раньше даты начала")
    if (date_to - date_from).days > 92:
        raise ValidationFailed("Расписание формируется не более чем на 3 месяца")
    q = select(Doctor).where(Doctor.is_active.is_(True))
    if tab_no:
        q = q.where(Doctor.tab_no == tab_no)
    result = {d.tab_no: generate(db, d, date_from, date_to) for d in db.scalars(q).all()}
    db.commit()
    return result


def nearest_free(db: Session, doctor: Doctor, limit: int = 5) -> dict:
    """Поиск свободных интервалов (А2): ближайшие даты у врача и у других врачей той же специальности."""
    now = clock.now()

    def free_days(tab_no: str, n: int):
        q = (select(ScheduleSlot.slot_date, func.count(), func.min(ScheduleSlot.time_start))
             .where(ScheduleSlot.tab_no == tab_no, ScheduleSlot.is_busy.is_(False),
                    (ScheduleSlot.slot_date > now.date())
                    | ((ScheduleSlot.slot_date == now.date()) & (ScheduleSlot.time_start > now.time())))
             .group_by(ScheduleSlot.slot_date).order_by(ScheduleSlot.slot_date).limit(n))
        return [{"date": d.isoformat(), "free_count": c, "first_time": _hm(t)} for d, c, t in db.execute(q)]

    others = db.scalars(select(Doctor).where(Doctor.specialty_code == doctor.specialty_code,
                                             Doctor.tab_no != doctor.tab_no, Doctor.is_active.is_(True))
                        .order_by(Doctor.last_name)).all()
    return {
        "doctor": free_days(doctor.tab_no, limit),
        "same_specialty": [{"tab_no": o.tab_no, "name": o.fio, "days": free_days(o.tab_no, 3)} for o in others],
    }


def _hm(t) -> str:
    if isinstance(t, str):  # SQLite возвращает MIN(time) строкой
        return t[:5]
    return t.strftime("%H:%M") if isinstance(t, time) else str(t)


# ------------------------------------------------------------------ рабочее время (администратор)
def _parse(t: str) -> time:
    try:
        return time.fromisoformat(t)
    except ValueError:
        raise ValidationFailed(f"Неверное время: {t}")


def work_rules_out(db: Session, d: Doctor) -> WorkRulesOut:
    rules = db.scalars(select(DoctorWorkRule).where(DoctorWorkRule.tab_no == d.tab_no)
                       .order_by(DoctorWorkRule.weekday)).all()
    lo, hi = db.execute(select(func.min(ScheduleSlot.slot_date), func.max(ScheduleSlot.slot_date))
                        .where(ScheduleSlot.tab_no == d.tab_no)).one()
    return WorkRulesOut(doctor=doctor_out(d), slots_from=lo, slots_to=hi,
                        rules=[WorkRuleIn(weekday=r.weekday, time_start=f"{r.time_start:%H:%M}",
                                          time_end=f"{r.time_end:%H:%M}") for r in rules])


def set_work_rules(db: Session, d: Doctor, rules: list[WorkRuleIn]) -> None:
    seen = set()
    for r in rules:
        if r.weekday in seen:
            raise ValidationFailed("День недели указан дважды")
        seen.add(r.weekday)
        if _parse(r.time_end) <= _parse(r.time_start):
            raise ValidationFailed("Окончание приёма должно быть позже начала")
    for old in db.scalars(select(DoctorWorkRule).where(DoctorWorkRule.tab_no == d.tab_no)):
        db.delete(old)
    db.flush()
    for r in rules:
        db.add(DoctorWorkRule(tab_no=d.tab_no, weekday=r.weekday, time_start=_parse(r.time_start),
                              time_end=_parse(r.time_end)))
    db.commit()
