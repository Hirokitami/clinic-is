"""Запись, перенос и отмена записи на приём (подсистема «Регистратура», функции 9–12).

create_appointment повторяет алгоритм СРО 11 (блок-схема, блоки 1–12) с уточнением У5 (СРО 9):
кроме действующей записи к тому же врачу проверяется запись пациента на то же время.
Защита от наложения записей – трёхуровневая: повторное чтение интервала, условное UPDATE
is_busy = 0 → 1 в одной транзакции с созданием записи и уникальный частичный индекс в БД.
"""
from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import BadRequest, Conflict, Forbidden, NotFound, ValidationFailed
from app.core.numbering import next_number
from app.modules.auth.models import UserAccount
from app.modules.notifications import service as sms
from app.modules.patients.models import Patient
from app.modules.schedule.models import ScheduleSlot
from app.modules.schedule.service import is_bookable

from .models import Appointment, AppointmentHistory


def load_for(db: Session, appt_no: str, user: UserAccount) -> Appointment:
    """Запись в пределах роли (Т13): пациенту – только своя, врачу – только к нему."""
    a = db.get(Appointment, appt_no)
    if not a:
        raise NotFound("Запись не найдена")
    if user.role_code == "PATIENT" and a.iin != user.iin:
        raise Forbidden("Запись другого пациента недоступна")
    if user.role_code == "DOCTOR" and a.slot.tab_no != user.tab_no:
        raise Forbidden("Запись к другому врачу недоступна")
    if user.role_code not in ("OPERATOR", "PATIENT", "DOCTOR", "ADMIN"):
        raise Forbidden("Нет прав на просмотр записи")
    return a


def list_appointments(db: Session, on=None, tab_no: str | None = None, iin: str | None = None,
                      status: str | None = None) -> list[Appointment]:
    q = select(Appointment).join(Appointment.slot)
    if iin:
        q = q.where(Appointment.iin == iin.strip())
    elif on:
        q = q.where(ScheduleSlot.slot_date == on)
    if tab_no:
        q = q.where(ScheduleSlot.tab_no == tab_no)
    if status:
        q = q.where(Appointment.status_code == status)
    order = (ScheduleSlot.slot_date.desc(), ScheduleSlot.time_start.desc()) if iin else         (ScheduleSlot.slot_date, ScheduleSlot.time_start)
    return list(db.scalars(q.order_by(*order).limit(500)))


def _slot_brief(s: ScheduleSlot) -> dict:
    return {"slot_id": s.slot_id, "date": s.slot_date.isoformat(), "time_start": s.time_start.strftime("%H:%M"),
            "doctor": s.doctor.short_name, "tab_no": s.tab_no}


def _overlapping(db: Session, iin: str, slot: ScheduleSlot, exclude: str | None = None) -> Appointment | None:
    """Действующая запись пациента, пересекающаяся по времени с интервалом (У5)."""
    q = (select(Appointment).join(Appointment.slot)
         .where(Appointment.iin == iin, Appointment.status_code == "PLANNED",
                ScheduleSlot.slot_date == slot.slot_date,
                and_(ScheduleSlot.time_start < slot.time_end, ScheduleSlot.time_end > slot.time_start)))
    if exclude:
        q = q.where(Appointment.appt_no != exclude)
    return db.scalars(q.limit(1)).first()


def _load_free_slot(db: Session, slot_id: str) -> ScheduleSlot:
    slot = db.get(ScheduleSlot, slot_id, populate_existing=True)
    if not slot or not is_bookable(slot):
        raise Conflict("Интервал уже занят или время приёма прошло. Выберите другой интервал.", code="SLOT_BUSY")
    return slot


def _occupy(db: Session, slot_id: str) -> None:
    res = db.execute(update(ScheduleSlot)
                     .where(ScheduleSlot.slot_id == slot_id, ScheduleSlot.is_busy.is_(False))
                     .values(is_busy=True))
    if res.rowcount != 1:  # интервал заняли одновременно другим пользователем (И6)
        raise Conflict("Интервал уже занят. Расписание обновлено, выберите другой интервал.", code="SLOT_BUSY")


def create_appointment(db: Session, user: UserAccount, iin: str, slot_id: str, reason: str,
                       confirm_existing: bool | None = None) -> Appointment:
    # Блок 1 – данные формы: пациент и интервал выбраны.
    patient = db.get(Patient, iin)
    if not patient:
        raise NotFound("Карта пациента не найдена. Запись без электронной карты не допускается.",
                       code="PATIENT_NOT_FOUND")
    # Блоки 2–3 – причина обращения заполнена? (И5)
    reason = (reason or "").strip()
    if not reason:
        raise ValidationFailed("Укажите причину обращения", fields={"reason": "Укажите причину обращения"})
    # Блоки 4–5 – интервал свободен и в рабочем времени врача? Повторное чтение из БД (И6).
    slot = _load_free_slot(db, slot_id)
    # У5 – у пациента нет другой записи на то же время.
    clash = _overlapping(db, iin, slot)
    if clash:
        raise Conflict("У пациента уже есть запись на это время", code="TIME_OVERLAP",
                       existing={"appt_no": clash.appt_no, **_slot_brief(clash.slot)})
    # Блоки 6–9 – действующая запись к этому врачу? (А4)
    existing = db.scalars(
        select(Appointment).join(Appointment.slot)
        .where(Appointment.iin == iin, Appointment.status_code == "PLANNED", ScheduleSlot.tab_no == slot.tab_no)
        .order_by(ScheduleSlot.slot_date, ScheduleSlot.time_start).limit(1)).first()
    if existing and confirm_existing is not True:
        info = {"appt_no": existing.appt_no, **_slot_brief(existing.slot)}
        if confirm_existing is False:  # блок 9
            raise Conflict("Запись не создана, выполните перенос записи", code="TRANSFER_REQUIRED", existing=info)
        raise Conflict(  # блок 7
            f"У пациента уже есть запись к этому врачу на {existing.slot.slot_date:%d.%m.%Y} "
            f"в {existing.slot.time_start:%H:%M}. Создать новую запись?",
            code="EXISTING_APPOINTMENT", existing=info)
    # Блок 10 – регистрация записи и отметка интервала занятым в одной транзакции.
    try:
        _occupy(db, slot.slot_id)
        appt = Appointment(appt_no=next_number(db, "Z"), iin=iin, slot_id=slot.slot_id, reason=reason,
                           status_code="PLANNED", created_at=clock.now(), created_by=user.login)
        db.add(appt)
        db.add(AppointmentHistory(appt_no=appt.appt_no, action="создание", new_slot_id=slot.slot_id,
                                  new_status="PLANNED", changed_at=clock.now(), changed_by=user.login))
        db.flush()
        db.refresh(appt)
        sms.notify(db, appt, "запись")  # блок 11
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("Интервал уже занят. Выберите другой интервал.", code="SLOT_BUSY")
    except Exception:
        db.rollback()
        raise
    return appt  # блок 12 – «Пациент записан»


def cancel_appointment(db: Session, user: UserAccount, appt: Appointment) -> Appointment:
    """Отмена (Т6.2): только «Запланирована», интервал освобождается, история и SMS."""
    if appt.status_code != "PLANNED":
        raise BadRequest("Отменить можно только запись в состоянии «Запланирована»", code="WRONG_STATUS")
    try:
        appt.status_code = "CANCELLED"
        db.execute(update(ScheduleSlot).where(ScheduleSlot.slot_id == appt.slot_id).values(is_busy=False))
        db.add(AppointmentHistory(appt_no=appt.appt_no, action="отмена", old_slot_id=appt.slot_id,
                                  old_status="PLANNED", new_status="CANCELLED", changed_at=clock.now(),
                                  changed_by=user.login))
        db.flush()
        sms.notify(db, appt, "отмена")
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(appt)
    return appt


def reschedule_appointment(db: Session, user: UserAccount, appt: Appointment, new_slot_id: str) -> Appointment:
    """Перенос (Т6.1): новый интервал того же врача; прежний освобождается; история сохраняется (Т7)."""
    if appt.status_code != "PLANNED":
        raise BadRequest("Перенести можно только запись в состоянии «Запланирована»", code="WRONG_STATUS")
    if new_slot_id == appt.slot_id:
        raise BadRequest("Выберите интервал, отличный от текущего", code="SAME_SLOT")
    new_slot = _load_free_slot(db, new_slot_id)
    if new_slot.tab_no != appt.slot.tab_no:
        raise BadRequest("Перенос выполняется на интервал того же врача", code="OTHER_DOCTOR")
    clash = _overlapping(db, appt.iin, new_slot, exclude=appt.appt_no)
    if clash:
        raise Conflict("У пациента уже есть запись на это время", code="TIME_OVERLAP",
                       existing={"appt_no": clash.appt_no, **_slot_brief(clash.slot)})
    old_slot_id = appt.slot_id
    try:
        _occupy(db, new_slot_id)
        db.execute(update(ScheduleSlot).where(ScheduleSlot.slot_id == old_slot_id).values(is_busy=False))
        appt.slot_id = new_slot_id
        db.add(AppointmentHistory(appt_no=appt.appt_no, action="перенос", old_slot_id=old_slot_id,
                                  new_slot_id=new_slot_id, old_status="PLANNED", new_status="PLANNED",
                                  changed_at=clock.now(), changed_by=user.login))
        db.flush()
        db.refresh(appt)
        sms.notify(db, appt, "перенос")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("Новый интервал занят. Перенос не выполнен, исходная запись сохранена.", code="SLOT_BUSY")
    except Exception:
        db.rollback()
        raise
    return appt


def mark_no_show(db: Session, user: UserAccount, appt: Appointment) -> Appointment:
    """Отметка неявки (функция 19): интервал остаётся в истории занятым."""
    if appt.status_code != "PLANNED":
        raise BadRequest("Неявку можно отметить только по записи в состоянии «Запланирована»", code="WRONG_STATUS")
    if appt.slot.starts_at > clock.now():
        raise BadRequest("Неявку можно отметить только после начала времени приёма", code="TOO_EARLY")
    appt.status_code = "NO_SHOW"
    db.add(AppointmentHistory(appt_no=appt.appt_no, action="неявка", old_status="PLANNED", new_status="NO_SHOW",
                              changed_at=clock.now(), changed_by=user.login))
    db.commit()
    db.refresh(appt)
    return appt
