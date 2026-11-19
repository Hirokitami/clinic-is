"""Подсистема «Процедуры» (функции 20–21, Т11.1–Т11.2)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import BadRequest, NotFound
from app.modules.auth.models import UserAccount

from .models import Prescription, ProcedureExecution
from .schemas import NurseRow, prescription_out


def procedures_for_day(db: Session, on: date, cabinet: str | None = None, state: str | None = None) -> list[NurseRow]:
    rows = []
    for r in db.scalars(select(Prescription).where(Prescription.start_date <= on).order_by(Prescription.rx_no)):
        done_before = sum(1 for e in r.executions if e.executed_at.date() < on)
        done_today = sum(1 for e in r.executions if e.executed_at.date() == on)
        if done_before >= r.sessions:
            continue  # курс завершён до выбранной даты
        remaining = r.sessions - len(r.executions)
        row_state = "completed" if remaining <= 0 else ("done_today" if done_today else "todo")
        if cabinet and r.procedure.cabinet_no != cabinet:
            continue
        if state and state != row_state:
            continue
        a = r.visit.appointment
        rows.append(NurseRow(prescription=prescription_out(r), patient_iin=a.iin, patient_fio=a.patient.fio,
                             doctor_name=a.slot.doctor.short_name, done_today=done_today, done_before=done_before,
                             remaining=max(remaining, 0), state=row_state))
    rows.sort(key=lambda x: (x.prescription.cabinet_no or "", x.patient_fio))
    return rows


def execute(db: Session, user: UserAccount, rx_no: str, note: str | None) -> tuple[int, int]:
    """Отметка выполнения: только по назначению врача, пока сеансы не исчерпаны."""
    r = db.get(Prescription, rx_no)
    if not r:
        raise NotFound("Назначение не найдено – отметка без назначения врача не допускается")
    done = len(r.executions)
    if done >= r.sessions:
        raise BadRequest(f"Все сеансы по назначению {rx_no} уже выполнены", code="SESSIONS_EXHAUSTED")
    if r.start_date > clock.today():
        raise BadRequest("Срок выполнения назначения ещё не наступил", code="TOO_EARLY")
    db.add(ProcedureExecution(rx_no=rx_no, executed_at=clock.now(), nurse_login=user.login,
                              note=(note or "").strip() or None))
    db.commit()
    return done + 1, r.sessions


def active_count(db: Session, on: date) -> int:
    return sum(1 for r in db.scalars(select(Prescription).where(Prescription.start_date <= on))
               if len(r.executions) < r.sessions)
