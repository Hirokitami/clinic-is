"""Отчёты для главного врача (перспектива 6 СРО 15) и показатели главного окна."""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.modules.appointments.models import Appointment
from app.modules.auth.models import UserAccount
from app.modules.lab.service import open_count
from app.modules.patients.models import Patient
from app.modules.procedures.service import active_count
from app.modules.schedule.models import Doctor, ScheduleSlot
from app.modules.visits.models import RenderedService, Visit


def clinic_report(db: Session, date_from: date | None, date_to: date | None) -> dict:
    """Загрузка врачей, неявки, обращаемость по специальностям, оказанные услуги за период."""
    date_to = date_to or clock.today()
    date_from = date_from or (date_to - timedelta(days=30))
    period = ScheduleSlot.slot_date.between(date_from, date_to)

    doctors = {d.tab_no: d for d in db.scalars(select(Doctor))}
    total_slots = dict(db.execute(select(ScheduleSlot.tab_no, func.count()).where(period)
                                  .group_by(ScheduleSlot.tab_no)).all())
    by_doc: dict[str, dict] = defaultdict(lambda: {"PLANNED": 0, "DONE": 0, "NO_SHOW": 0, "CANCELLED": 0})
    by_day: dict[date, int] = defaultdict(int)
    by_spec: dict[str, int] = defaultdict(int)
    rows = db.execute(select(ScheduleSlot.tab_no, ScheduleSlot.slot_date, Appointment.status_code)
                      .join(Appointment.slot).where(period)).all()
    for tab, d, st in rows:
        by_doc[tab][st] += 1
        if st != "CANCELLED":
            by_day[d] += 1
            by_spec[doctors[tab].specialty.name] += 1

    doctor_rows = []
    for tab, d in sorted(doctors.items(), key=lambda x: x[1].last_name):
        c = by_doc[tab]
        busy = c["PLANNED"] + c["DONE"] + c["NO_SHOW"]
        slots = total_slots.get(tab, 0)
        finished = c["DONE"] + c["NO_SHOW"]
        doctor_rows.append({
            "tab_no": tab, "name": d.fio, "specialty": d.specialty.name, "slots": slots, "busy": busy,
            "load_pct": round(100 * busy / slots, 1) if slots else 0.0, **{k.lower(): v for k, v in c.items()},
            "no_show_pct": round(100 * c["NO_SHOW"] / finished, 1) if finished else 0.0})

    svc = db.execute(select(RenderedService).join(RenderedService.visit).join(Visit.appointment)
                     .join(Appointment.slot).where(period)).scalars().all()
    svc_agg: dict[str, dict] = {}
    for s in svc:
        row = svc_agg.setdefault(s.service_code, {"code": s.service_code, "name": s.service.name, "qty": 0,
                                                  "amount_kzt": 0.0})
        row["qty"] += s.qty
        row["amount_kzt"] += float(s.price_kzt) * s.qty

    totals = {k: sum(r[k] for r in doctor_rows) for k in ("slots", "busy", "planned", "done", "no_show", "cancelled")}
    fin = totals["done"] + totals["no_show"]
    totals["load_pct"] = round(100 * totals["busy"] / totals["slots"], 1) if totals["slots"] else 0.0
    totals["no_show_pct"] = round(100 * totals["no_show"] / fin, 1) if fin else 0.0
    totals["revenue_kzt"] = sum(r["amount_kzt"] for r in svc_agg.values())
    totals["new_patients"] = db.scalar(select(func.count()).select_from(Patient)
                                       .where(Patient.reg_date.between(date_from, date_to))) or 0

    days = []
    d = date_from
    while d <= date_to:
        days.append({"date": d.isoformat(), "appointments": by_day.get(d, 0)})
        d += timedelta(days=1)

    return {"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "totals": totals,
            "doctors": doctor_rows, "by_specialty": [{"specialty": k, "appointments": v}
                                                     for k, v in sorted(by_spec.items(), key=lambda x: -x[1])],
            "by_day": days, "services": sorted(svc_agg.values(), key=lambda x: -x["amount_kzt"])}


def dashboard(db: Session, user: UserAccount) -> dict:
    """Главное окно: показатели на сегодня в пределах роли пользователя."""
    today = clock.today()
    planned_today = (select(func.count()).select_from(Appointment).join(Appointment.slot)
                     .where(ScheduleSlot.slot_date == today, Appointment.status_code == "PLANNED"))
    stats: dict = {"today": today.isoformat()}
    if user.role_code in ("OPERATOR", "ADMIN"):
        stats["appointments_today"] = db.scalar(planned_today)
        stats["patients"] = db.scalar(select(func.count()).select_from(Patient))
        stats["free_slots_today"] = db.scalar(
            select(func.count()).select_from(ScheduleSlot).where(
                ScheduleSlot.slot_date == today, ScheduleSlot.is_busy.is_(False),
                ScheduleSlot.time_start > clock.now().time()))
    if user.role_code == "DOCTOR":
        stats["appointments_today"] = db.scalar(planned_today.where(ScheduleSlot.tab_no == user.tab_no))
        stats["done_today"] = db.scalar(
            select(func.count()).select_from(Appointment).join(Appointment.slot)
            .where(ScheduleSlot.slot_date == today, ScheduleSlot.tab_no == user.tab_no,
                   Appointment.status_code == "DONE"))
    if user.role_code == "NURSE":
        stats["active_prescriptions"] = active_count(db, today)
    if user.role_code == "LAB":
        stats["referrals_open"] = open_count(db)
    if user.role_code == "PATIENT":
        nxt = db.scalars(select(Appointment).join(Appointment.slot)
                         .where(Appointment.iin == user.iin, Appointment.status_code == "PLANNED",
                                ScheduleSlot.slot_date >= today)
                         .order_by(ScheduleSlot.slot_date, ScheduleSlot.time_start).limit(1)).first()
        stats["next_appointment"] = None if not nxt else {
            "appt_no": nxt.appt_no, "date": nxt.slot.slot_date.isoformat(),
            "time": f"{nxt.slot.time_start:%H:%M}", "doctor": nxt.slot.doctor.fio,
            "specialty": nxt.slot.doctor.specialty.name, "cabinet_no": nxt.slot.cabinet_no}
    return stats
