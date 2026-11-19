"""Внесение результатов исследований сотрудником лаборатории (перспектива 4 СРО 15)."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import BadRequest, NotFound, ValidationFailed
from app.core.numbering import next_number
from app.modules.auth.models import UserAccount

from .models import Referral, TestResult


def list_referrals(db: Session, status: str | None) -> list[Referral]:
    q = select(Referral).order_by(Referral.created_at)
    if status:
        q = q.where(Referral.status == status)
    return list(db.scalars(q.limit(300)))


def open_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Referral).where(Referral.status == "ORDERED")) or 0


def record_result(db: Session, user: UserAccount, ref_no: str, value_text: str, done_date: date | None) -> TestResult:
    ref = db.get(Referral, ref_no)
    if not ref:
        raise NotFound("Направление не найдено")
    if ref.status == "DONE":
        raise BadRequest("Результат по направлению уже внесён", code="ALREADY_DONE")
    if not (value_text or "").strip():
        raise ValidationFailed("Укажите результат исследования", fields={"value_text": "Укажите результат"})
    done = done_date or clock.today()
    if done > clock.today():
        raise ValidationFailed("Дата выполнения не может быть позже текущей",
                               fields={"done_date": "Дата позже текущей"})
    a = ref.visit.appointment
    try:
        res = TestResult(result_no=next_number(db, "L"), iin=a.iin, test_code=ref.test_code, tab_no=a.slot.tab_no,
                         referral_no=ref.ref_no, done_date=done, value_text=value_text.strip(),
                         entered_by=user.login)
        db.add(res)
        ref.status = "DONE"
        db.commit()
    except Exception:
        db.rollback()
        raise
    return res
