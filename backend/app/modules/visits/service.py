"""Подсистема «Приём пациента»: история пациента, фиксация и изменение результатов приёма (функции 14–19)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import BadRequest, Forbidden, NotFound, ValidationFailed
from app.core.numbering import next_number
from app.modules.appointments.models import Appointment, AppointmentHistory
from app.modules.appointments.schemas import appointment_out
from app.modules.auth.models import UserAccount
from app.modules.lab.models import Referral, TestResult
from app.modules.lab.schemas import referral_out, test_result_out
from app.modules.patients.models import Patient
from app.modules.patients.schemas import patient_out
from app.modules.procedures.models import Prescription
from app.modules.procedures.schemas import prescription_out
from app.modules.references.models import Diagnosis, ProcedureType, Service, TestType
from app.modules.schedule.models import ScheduleSlot
from app.modules.schedule.schemas import slot_out
from app.modules.schedule.service import day_slots, is_bookable

from .models import RenderedService, Visit, VisitChange
from .schemas import DoctorDayRow, PatientHistoryOut, VisitChangeOut, VisitEditIn, VisitIn, VisitOut, service_line_out


def visit_out(db: Session, v: Visit, full: bool = True) -> VisitOut:
    s = v.appointment.slot
    out = VisitOut(visit_no=v.visit_no, appt_no=v.appt_no, date=s.slot_date, complaints=v.complaints,
                   icd_code=v.icd_code, diagnosis_name=v.diagnosis.name, conclusion=v.conclusion,
                   finished_at=v.finished_at, author=v.author, doctor_name=s.doctor.fio,
                   specialty_name=s.doctor.specialty.name, tab_no=s.tab_no)
    if full:
        out.prescriptions = [prescription_out(r) for r in db.scalars(
            select(Prescription).where(Prescription.visit_no == v.visit_no).order_by(Prescription.rx_no))]
        out.referrals = [referral_out(r) for r in db.scalars(
            select(Referral).where(Referral.visit_no == v.visit_no).order_by(Referral.ref_no))]
        out.services = [service_line_out(r) for r in db.scalars(
            select(RenderedService).where(RenderedService.visit_no == v.visit_no).order_by(RenderedService.line_no))]
        out.services_total = sum(x.amount_kzt for x in out.services)
        out.changes = [VisitChangeOut(field=c.field, old_value=c.old_value, new_value=c.new_value,
                                      changed_at=c.changed_at, changed_by=c.changed_by)
                       for c in db.scalars(select(VisitChange).where(VisitChange.visit_no == v.visit_no)
                                           .order_by(VisitChange.id))]
    return out


def patient_history(db: Session, iin: str) -> PatientHistoryOut:
    p = db.get(Patient, iin)
    if not p:
        raise NotFound("Пациент не найден")
    visits = db.scalars(select(Visit).join(Visit.appointment).where(Appointment.iin == iin)
                        .order_by(Visit.finished_at.desc())).all()
    rx = db.scalars(select(Prescription).join(Prescription.visit).join(Visit.appointment)
                    .where(Appointment.iin == iin).order_by(Prescription.created_at.desc())).all()
    refs = db.scalars(select(Referral).join(Referral.visit).join(Visit.appointment)
                      .where(Appointment.iin == iin).order_by(Referral.created_at.desc())).all()
    tests = db.scalars(select(TestResult).where(TestResult.iin == iin).order_by(TestResult.done_date.desc())).all()
    return PatientHistoryOut(
        patient=patient_out(p), visits=[visit_out(db, v) for v in visits],
        prescriptions=[prescription_out(r) for r in rx], referrals=[referral_out(r) for r in refs],
        tests=[test_result_out(t) for t in tests])


def doctor_can_see(db: Session, tab_no: str, iin: str) -> bool:
    """Т13: врачу доступны карты пациентов, записанных к нему на приём."""
    return db.scalar(select(Appointment.appt_no).join(Appointment.slot)
                     .where(Appointment.iin == iin, ScheduleSlot.tab_no == tab_no).limit(1)) is not None


def _validate_visit(db: Session, data: VisitIn | VisitEditIn) -> dict:
    errors = {}
    if not data.complaints.strip():
        errors["complaints"] = "Укажите жалобы пациента"
    if not data.icd_code:
        errors["icd_code"] = "Выберите основной диагноз из справочника МКБ-10"
    elif not db.get(Diagnosis, data.icd_code):
        errors["icd_code"] = "Диагноз отсутствует в справочнике МКБ-10"
    return errors


def save_visit(db: Session, user: UserAccount, appt: Appointment, data: VisitIn) -> Visit:
    """Фиксация результатов приёма (функции 15–18): жалобы, диагноз, заключение, назначения,
    направления, оказанные услуги; запись переводится в «Проведена»."""
    if appt.status_code != "PLANNED":
        raise BadRequest("Результаты можно внести только по записи в состоянии «Запланирована»", code="WRONG_STATUS")
    if appt.slot.slot_date > clock.today():
        raise BadRequest("Приём ещё не наступил: результаты вносятся в день приёма", code="TOO_EARLY")
    errors = _validate_visit(db, data)
    for i, r in enumerate(data.prescriptions):
        if not db.get(ProcedureType, r.procedure_code):
            errors[f"prescriptions.{i}"] = "Процедура отсутствует в справочнике"
    for i, r in enumerate(data.referrals):
        if not db.get(TestType, r.test_code):
            errors[f"referrals.{i}"] = "Исследование отсутствует в справочнике"
    services = {}
    for i, r in enumerate(data.services):
        svc = db.get(Service, r.service_code)
        if not svc or not svc.is_active:
            errors[f"services.{i}"] = "Услуга отсутствует в справочнике"
        else:
            services[r.service_code] = svc
    if errors:
        raise ValidationFailed("Проверьте заполнение формы приёма", fields=errors)

    now = clock.now()
    try:
        visit = Visit(visit_no=next_number(db, "P"), appt_no=appt.appt_no, complaints=data.complaints.strip(),
                      icd_code=data.icd_code, conclusion=(data.conclusion or "").strip() or None,
                      finished_at=now, author=user.login)
        db.add(visit)
        db.flush()
        for r in data.prescriptions:
            db.add(Prescription(rx_no=next_number(db, "N"), visit_no=visit.visit_no, procedure_code=r.procedure_code,
                                sessions=r.sessions, instructions=(r.instructions or "").strip() or None,
                                start_date=now.date(), created_at=now, author=user.login))
        for r in data.referrals:
            db.add(Referral(ref_no=next_number(db, "D"), visit_no=visit.visit_no, test_code=r.test_code,
                            note=(r.note or "").strip() or None, status="ORDERED", created_at=now,
                            author=user.login))
        for r in data.services:
            db.add(RenderedService(line_no=next_number(db, "U"), visit_no=visit.visit_no,
                                   service_code=r.service_code, qty=r.qty,
                                   price_kzt=services[r.service_code].price_kzt))
        appt.status_code = "DONE"
        db.add(AppointmentHistory(appt_no=appt.appt_no, action="приём проведён", old_status="PLANNED",
                                  new_status="DONE", changed_at=now, changed_by=user.login))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return visit


def edit_visit(db: Session, user: UserAccount, visit: Visit, data: VisitEditIn) -> Visit:
    """Изменение результатов приёма (Т10) с сохранением прежних значений в истории."""
    errors = _validate_visit(db, data)
    if errors:
        raise ValidationFailed("Проверьте заполнение формы приёма", fields=errors)
    new = {"complaints": data.complaints.strip(), "icd_code": data.icd_code,
           "conclusion": (data.conclusion or "").strip() or None}
    now = clock.now()
    changed = False
    for field, value in new.items():
        old = getattr(visit, field)
        if old != value:
            db.add(VisitChange(visit_no=visit.visit_no, field=field, old_value=old, new_value=value,
                               changed_at=now, changed_by=user.login))
            setattr(visit, field, value)
            changed = True
    if not changed:
        raise BadRequest("Изменений нет", code="NO_CHANGES")
    db.commit()
    db.refresh(visit)
    return visit


def doctor_day(db: Session, tab_no: str, on: date) -> list[DoctorDayRow]:
    """Пациенты на приём (функция 13, С7): интервалы дня с записями и отметкой о проведённом приёме."""
    slots = day_slots(db, tab_no, on)
    appts = {a.slot_id: a for a in db.scalars(
        select(Appointment).where(Appointment.slot_id.in_([s.slot_id for s in slots]),
                                  Appointment.status_code != "CANCELLED"))}
    visits = {v.appt_no: v.visit_no for v in db.scalars(
        select(Visit).where(Visit.appt_no.in_([a.appt_no for a in appts.values()])))}
    rows = []
    for s in slots:
        a = appts.get(s.slot_id)
        rows.append(DoctorDayRow(slot=slot_out(s, is_bookable(s)), appointment=appointment_out(a) if a else None,
                                 visit_no=visits.get(a.appt_no) if a else None))
    return rows


def own_appointment(db: Session, appt_no: str, user: UserAccount) -> Appointment:
    a = db.get(Appointment, appt_no)
    if not a:
        raise NotFound("Запись не найдена")
    if a.slot.tab_no != user.tab_no:
        raise Forbidden("Запись к другому врачу недоступна")
    return a


def visit_of(db: Session, appt_no: str) -> Visit | None:
    return db.scalars(select(Visit).where(Visit.appt_no == appt_no)).first()


def own_visit(db: Session, visit_no: str, user: UserAccount) -> Visit:
    v = db.get(Visit, visit_no)
    if not v:
        raise NotFound("Приём не найден")
    if v.appointment.slot.tab_no != user.tab_no:
        raise Forbidden("Изменять результаты может только врач, проводивший приём")
    return v
