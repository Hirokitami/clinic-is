"""Подтверждение записи пациенту (Т8, функция 12).

Шлюз выбирается настройкой CLINIC_SMS_GATEWAY. Сейчас реализован только "mock": сообщение
сохраняется в журнале sms_outbox со статусом «имитация отправки». Для подключения реального
шлюза достаточно реализовать класс с методом send() и зарегистрировать его в GATEWAYS.
"""
import logging
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import settings

from .models import SmsOutbox

if TYPE_CHECKING:
    from app.modules.appointments.models import Appointment

log = logging.getLogger(__name__)


class SmsGateway(Protocol):
    def send(self, phone: str, text: str) -> str:
        """Отправляет сообщение, возвращает статус для журнала. Исключение – сообщение не доставлено."""


class MockGateway:
    def send(self, phone: str, text: str) -> str:
        log.info("SMS (имитация) %s: %s", phone, text)
        return "имитация отправки"


GATEWAYS: dict[str, type] = {"mock": MockGateway}


def _gateway() -> SmsGateway:
    return GATEWAYS.get(settings.sms_gateway, MockGateway)()


def format_date(d) -> str:
    return d.strftime("%d.%m.%Y")


def compose(a: "Appointment", action: str) -> str:
    s = a.slot
    doctor = s.doctor.short_name
    when = f"{format_date(s.slot_date)} в {s.time_start:%H:%M}"
    if action == "отмена":
        return f"{settings.clinic_name}: запись {a.appt_no} к врачу {doctor} на {when} отменена."
    verb = "перенесена" if action == "перенос" else "подтверждена"
    return (f"{settings.clinic_name}: запись {verb}. {s.doctor.specialty.name} {doctor}, {when}, "
            f"каб. {s.cabinet_no} ({s.cabinet.floor_no} этаж). Номер {a.appt_no}.")


def notify(db: Session, a: "Appointment", action: str = "запись") -> SmsOutbox:
    """Формирует и отправляет SMS. Сбой шлюза не отменяет запись (И8) – статус фиксируется в журнале."""
    text = compose(a, action)
    try:
        status = _gateway().send(a.patient.mobile_phone, text)
    except Exception as exc:  # noqa: BLE001 – любой сбой шлюза = недоставка
        log.warning("SMS не доставлено: %s", exc)
        status = "не доставлено"
    msg = SmsOutbox(appt_no=a.appt_no, phone=a.patient.mobile_phone, text=text, status=status,
                    created_at=clock.now())
    db.add(msg)
    return msg


def last_for(db: Session, appt_no: str) -> SmsOutbox | None:
    return db.scalars(select(SmsOutbox).where(SmsOutbox.appt_no == appt_no).order_by(SmsOutbox.id.desc())
                      .limit(1)).first()
