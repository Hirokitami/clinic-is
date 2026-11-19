"""Регистрация, поиск и изменение данных пациента (функции 3–5, Т1–Т3)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import NotFound, ValidationFailed

from .models import Patient
from .schemas import PatientIn, patient_out

EDITABLE = ("last_name", "first_name", "middle_name", "birth_date", "sex", "mobile_phone", "address",
            "doc_type", "doc_no")
DUPLICATE = "Карта с таким ИИН уже существует"


def iin_valid(iin: str | None) -> bool:
    return bool(iin) and len(iin) == 12 and iin.isdigit()


def validate(db: Session, data: PatientIn, new: bool) -> dict[str, str]:
    errors: dict[str, str] = {}
    if new:
        if not iin_valid(data.iin):
            errors["iin"] = "ИИН должен содержать 12 цифр"
        elif db.get(Patient, data.iin):
            errors["iin"] = DUPLICATE
    for key, name in (("last_name", "фамилию"), ("first_name", "имя"), ("birth_date", "дату рождения"),
                      ("mobile_phone", "мобильный телефон")):
        if not getattr(data, key):
            errors[key] = f"Укажите {name}"
    if data.birth_date and data.birth_date > clock.today():
        errors["birth_date"] = "Дата рождения не может быть позже текущей даты"
    if data.mobile_phone:
        digits = "".join(ch for ch in data.mobile_phone if ch.isdigit())
        if len(digits) != 11:
            errors["mobile_phone"] = "Телефон должен содержать 11 цифр, например +7 701 234 56 78"
    if data.sex not in (None, "", "М", "Ж"):
        errors["sex"] = "Пол: «М» или «Ж»"
    return errors


def get_or_404(db: Session, iin: str) -> Patient:
    p = db.get(Patient, iin)
    if not p:
        raise NotFound("Пациент не найден", code="PATIENT_NOT_FOUND")
    return p


def find_by_iin(db: Session, iin: str) -> Patient:
    iin = iin.strip()
    if not iin_valid(iin):  # И2
        raise ValidationFailed("ИИН должен содержать 12 цифр", fields={"iin": "ИИН должен содержать 12 цифр"})
    p = db.get(Patient, iin)
    if not p:  # И3
        raise NotFound(f"Пациент с ИИН {iin} не найден. Необходимо зарегистрировать пациента.",
                       code="PATIENT_NOT_FOUND", iin=iin)
    return p


def find_by_name(db: Session, fio: str | None, birth_date: date | None) -> list[Patient]:
    """А1: поиск по ФИО и дате рождения."""
    parts = (fio or "").split()
    if not parts or not birth_date:
        raise ValidationFailed("Для поиска укажите фамилию (ФИО) и дату рождения")
    q = select(Patient).where(Patient.last_name.ilike(parts[0] + "%"), Patient.birth_date == birth_date)
    if len(parts) > 1:
        q = q.where(Patient.first_name.ilike(parts[1] + "%"))
    found = db.scalars(q.order_by(Patient.last_name)).all()
    if not found:
        raise NotFound("Карты с такими ФИО и датой рождения не найдены", code="PATIENT_NOT_FOUND")
    return list(found)


def register(db: Session, data: PatientIn) -> Patient:
    errors = validate(db, data, new=True)
    if errors:
        existing = db.get(Patient, data.iin) if errors.get("iin") == DUPLICATE else None
        raise ValidationFailed("Проверьте данные пациента", fields=errors,
                               existing=patient_out(existing).model_dump(mode="json") if existing else None)
    p = Patient(iin=data.iin, reg_date=clock.today(), **{k: (getattr(data, k) or None) for k in EDITABLE})
    db.add(p)
    db.commit()
    return p


def update(db: Session, p: Patient, data: PatientIn) -> Patient:
    errors = validate(db, data, new=False)
    if errors:
        raise ValidationFailed("Проверьте данные пациента", fields=errors)
    for k in EDITABLE:
        setattr(p, k, getattr(data, k) or None)
    db.commit()
    return p
