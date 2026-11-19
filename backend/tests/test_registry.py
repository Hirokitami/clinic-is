"""Регистратура: поиск и регистрация пациента, запись на приём (алгоритм СРО 11), отмена, перенос."""
from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflict
from app.modules.appointments.models import Appointment
from app.modules.auth.models import UserAccount
from app.modules.schedule.models import ScheduleSlot
from app.modules.appointments import service as booking

from .conftest import TODAY, free_slot

DANA = "040512650123"  # есть действующая запись к кардиологу D-017 (среда, 10:00)
IVANOV = "880915300456"
WED = TODAY + timedelta(days=2)
TUE = TODAY + timedelta(days=1)

NEW_PATIENT = {"iin": "990101300111", "last_name": "Тестов", "first_name": "Тест", "middle_name": "Тестович",
               "birth_date": "1999-01-01", "sex": "М", "mobile_phone": "+7 700 000 00 01"}


# ------------------------------------------------------------------ поиск (Т1, А1, И2, И3)
def test_find_by_iin(login):
    c = login("operator.reg1")
    r = c.get("/api/patients/search", params={"iin": DANA})
    assert r.status_code == 200 and r.json()[0]["fio"] == "Ахметова Дана Ерлановна"


def test_iin_format_checked_before_search(login):
    r = login("operator.reg1").get("/api/patients/search", params={"iin": "12345"})
    assert r.status_code == 422 and r.json()["detail"]["message"] == "ИИН должен содержать 12 цифр"


def test_iin_not_found_offers_registration(login):
    r = login("operator.reg1").get("/api/patients/search", params={"iin": "000000000000"})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "PATIENT_NOT_FOUND"


def test_find_by_fio_and_birth_date(login):
    r = login("operator.reg1").get("/api/patients/search", params={"fio": "Иван Серг", "birth_date": "1988-09-15"})
    assert r.status_code == 200 and [p["iin"] for p in r.json()] == [IVANOV]


# ------------------------------------------------------------------ регистрация (Т1–Т3)
def test_register_patient(login):
    c = login("operator.reg1")
    r = c.post("/api/patients", json=NEW_PATIENT)
    assert r.status_code == 201, r.text
    assert c.get(f"/api/patients/{NEW_PATIENT['iin']}").json()["reg_date"] == TODAY.isoformat()


def test_register_duplicate_iin_rejected(login):
    r = login("operator.reg1").post("/api/patients", json={**NEW_PATIENT, "iin": DANA})
    d = r.json()["detail"]
    assert r.status_code == 422 and d["fields"]["iin"] == "Карта с таким ИИН уже существует"
    assert d["existing"]["iin"] == DANA


def test_register_required_fields(login):
    r = login("operator.reg1").post("/api/patients", json={"iin": "990101300112"})
    fields = r.json()["detail"]["fields"]
    assert r.status_code == 422 and {"last_name", "first_name", "birth_date", "mobile_phone"} <= set(fields)


def test_update_patient(login):
    c = login("operator.reg1")
    p = c.get(f"/api/patients/{IVANOV}").json()
    p["address"] = "г. Алматы, ул. Новая, 1"
    r = c.put(f"/api/patients/{IVANOV}", json=p)
    assert r.status_code == 200 and r.json()["address"] == "г. Алматы, ул. Новая, 1"


# ------------------------------------------------------------------ расписание (Т4, А2, И4)
def test_schedule_shows_busy_and_free(login):
    r = login("operator.reg1").get("/api/schedule/D-017", params={"on": WED.isoformat()})
    states = [s["state"] for s in r.json()["slots"]]
    assert r.json()["works"] and states[0] == "busy" and states[1] == "free" and states[2] == "busy"


def test_doctor_day_off(login):
    sunday = TODAY + timedelta(days=6)
    r = login("operator.reg1").get("/api/schedule/D-017", params={"on": sunday.isoformat()})
    assert r.json()["works"] is False and r.json()["work_days"] == [0, 1, 2, 3, 4]


def test_nearest_free_includes_same_specialty(login):
    r = login("operator.reg1").get("/api/schedule/D-001/nearest").json()
    assert r["doctor"] and r["same_specialty"][0]["tab_no"] == "D-002"


# ------------------------------------------------------------------ запись (СРО 11, блоки 1–12)
def test_create_appointment_ok(login, Session):
    c = login("operator.reg1")
    slot = free_slot(c, "D-001", TUE)
    r = c.post("/api/appointments", json={"iin": IVANOV, "slot_id": slot, "reason": "Кашель"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["message"] == "Пациент записан" and body["appointment"]["status_code"] == "PLANNED"
    assert "подтверждена" in body["sms"]["text"] and "каб. 201" in body["sms"]["text"]
    with Session() as db:
        assert db.get(ScheduleSlot, slot).is_busy


def test_reason_required(login):
    c = login("operator.reg1")
    r = c.post("/api/appointments", json={"iin": IVANOV, "slot_id": free_slot(c, "D-001", TUE), "reason": "  "})
    assert r.status_code == 422 and r.json()["detail"]["fields"]["reason"] == "Укажите причину обращения"


def test_busy_slot_rejected(login):
    c = login("operator.reg1")
    busy = [s for s in c.get("/api/schedule/D-017", params={"on": WED.isoformat()}).json()["slots"] if s["is_busy"]]
    r = c.post("/api/appointments", json={"iin": IVANOV, "slot_id": busy[0]["slot_id"], "reason": "x"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "SLOT_BUSY"


def test_past_slot_rejected(login):
    c = login("operator.reg1")
    slots = c.get("/api/schedule/D-001", params={"on": (TODAY - timedelta(days=2)).isoformat()}).json()["slots"]  # суббота
    free_past = next(s for s in slots if not s["is_busy"])
    r = c.post("/api/appointments", json={"iin": IVANOV, "slot_id": free_past["slot_id"], "reason": "x"})
    assert r.status_code == 409


def test_existing_appointment_warning_and_confirm(login):
    """А4: у Даны уже есть запись к D-017 – предупреждение, отказ (блок 9) и подтверждение (блок 10)."""
    c = login("operator.reg1")
    slot = free_slot(c, "D-017", TODAY + timedelta(days=3))
    r = c.post("/api/appointments", json={"iin": DANA, "slot_id": slot, "reason": "Повторный приём"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "EXISTING_APPOINTMENT"
    assert r.json()["detail"]["existing"]["time_start"] == "10:00"
    r = c.post("/api/appointments", json={"iin": DANA, "slot_id": slot, "reason": "x", "confirm_existing": False})
    assert r.json()["detail"]["message"] == "Запись не создана, выполните перенос записи"
    r = c.post("/api/appointments", json={"iin": DANA, "slot_id": slot, "reason": "x", "confirm_existing": True})
    assert r.status_code == 201


def test_same_time_other_doctor_rejected(login):
    """У5: запись пациента на то же время к другому врачу не допускается."""
    c = login("operator.reg1")
    # У Даны – D-017 в среду 10:00–10:30; терапевт D-001 в среду 10:00 – пересечение.
    slots = c.get("/api/schedule/D-001", params={"on": WED.isoformat()}).json()["slots"]
    clash = next(s for s in slots if s["time_start"] == "10:00")
    r = c.post("/api/appointments", json={"iin": DANA, "slot_id": clash["slot_id"], "reason": "Насморк"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "TIME_OVERLAP"


def test_race_second_booking_rejected(Session):
    """И6: интервал занят другим пользователем после чтения – условное UPDATE не проходит."""
    with Session() as db:
        user = db.get(UserAccount, "operator.reg1")
        slot = db.query(ScheduleSlot).filter_by(tab_no="D-002", slot_date=TUE, is_busy=False).first()
        booking.create_appointment(db, user, IVANOV, slot.slot_id, "Первый")
    with Session() as db, pytest.raises(Conflict):
        booking._occupy(db, slot.slot_id)


def test_db_unique_index_blocks_double_booking(Session):
    with Session() as db:
        a = db.query(Appointment).filter_by(status_code="PLANNED").first()
        db.add(Appointment(appt_no="Z-TEST-1", iin=IVANOV, slot_id=a.slot_id, reason="обход формы",
                           status_code="PLANNED", created_by="operator.reg1"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_ticket_details(login):
    c = login("operator.reg1")
    no = c.post("/api/appointments", json={"iin": IVANOV, "slot_id": free_slot(c, "D-001", TUE),
                                           "reason": "Кашель"}).json()["appointment"]["appt_no"]
    t = c.get(f"/api/appointments/{no}").json()
    assert t["doctor"]["fio"] == "Сейткали Айгерим Болатовна" and t["cabinet_no"] == "201"
    assert t["history"][0]["action"] == "создание"


def test_new_patient_can_be_booked(login):
    c = login("operator.reg1")
    c.post("/api/patients", json=NEW_PATIENT)
    r = c.post("/api/appointments", json={"iin": NEW_PATIENT["iin"], "slot_id": free_slot(c, "D-001", TUE),
                                          "reason": "Первичный осмотр"})
    assert r.status_code == 201


# ------------------------------------------------------------------ отмена и перенос (Т6.1, Т6.2, Т7)
def _dana_wed(c):
    return next(a for a in c.get("/api/appointments", params={"iin": DANA}).json() if a["status_code"] == "PLANNED")


def test_cancel_frees_slot(login, Session):
    c = login("operator.reg1")
    a = _dana_wed(c)
    r = c.post(f"/api/appointments/{a['appt_no']}/cancel")
    assert r.status_code == 200 and r.json()["appointment"]["status_code"] == "CANCELLED"
    assert "отменена" in r.json()["sms"]["text"]
    with Session() as db:
        assert not db.get(ScheduleSlot, a["slot_id"]).is_busy
    # освобождённый интервал снова доступен для записи
    r = c.post("/api/appointments", json={"iin": "950302400789", "slot_id": a["slot_id"], "reason": "x"})
    assert r.status_code == 201, r.text


def test_cancel_done_forbidden(login):
    c = login("operator.reg1")
    done = next(a for a in c.get("/api/appointments", params={"iin": DANA}).json() if a["status_code"] == "DONE")
    assert c.post(f"/api/appointments/{done['appt_no']}/cancel").status_code == 400


def test_reschedule_keeps_history(login, Session):
    c = login("operator.reg1")
    a = _dana_wed(c)
    new = free_slot(c, "D-017", TODAY + timedelta(days=3))
    r = c.post(f"/api/appointments/{a['appt_no']}/reschedule", json={"slot_id": new})
    assert r.status_code == 200, r.text
    hist = r.json()["appointment"]["history"]
    assert hist[-1]["action"] == "перенос" and hist[-1]["old_time"] == "10:00"
    with Session() as db:
        assert not db.get(ScheduleSlot, a["slot_id"]).is_busy and db.get(ScheduleSlot, new).is_busy


def test_reschedule_to_busy_rejected(login, Session):
    c = login("operator.reg1")
    a = _dana_wed(c)
    busy = next(s for s in c.get("/api/schedule/D-017", params={"on": WED.isoformat()}).json()["slots"]
                if s["is_busy"] and s["slot_id"] != a["slot_id"])
    r = c.post(f"/api/appointments/{a['appt_no']}/reschedule", json={"slot_id": busy["slot_id"]})
    assert r.status_code == 409
    with Session() as db:
        assert db.get(Appointment, a["appt_no"]).slot_id == a["slot_id"]


def test_sms_log(login):
    c = login("operator.reg1")
    c.post(f"/api/appointments/{_dana_wed(c)['appt_no']}/cancel")
    assert c.get("/api/sms").json()[0]["status"] == "имитация отправки"
