"""Врач, медсестра, лаборатория, личный кабинет, администратор, разграничение доступа (Т9–Т13)."""
from datetime import timedelta

from .conftest import TODAY, free_slot

DANA = "040512650123"
IVANOV = "880915300456"


# ------------------------------------------------------------------ доступ (Т13, И1)
def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"login": "operator.reg1", "password": "bad"})
    assert r.status_code == 401


def test_requires_login(client):
    assert client.get("/api/patients/search", params={"iin": DANA}).status_code == 401


def test_nurse_cannot_book(login):
    c = login("nurse.omarova")
    r = c.post("/api/appointments", json={"iin": DANA, "slot_id": "x", "reason": "x"})
    assert r.status_code == 403
    assert c.get("/api/patients/search", params={"iin": DANA}).status_code == 403


def test_me(login):
    assert login("doctor.akhmetov").get("/api/auth/me").json()["role_name"] == "Врач-специалист"


# ------------------------------------------------------------------ врач (С7–С9)
def test_doctor_day(login):
    rows = login("doctor.akhmetov").get("/api/doctor/day", params={"on": TODAY.isoformat()}).json()
    booked = [r for r in rows if r["appointment"]]
    assert [r["appointment"]["patient_fio"] for r in booked] == ["Смагулова Алия", "Иванов Сергей Петрович"]


def test_doctor_access_restriction(login):
    c = login("doctor.seitkali")  # терапевт D-001
    assert c.get(f"/api/doctor/patients/{IVANOV}/history").status_code == 200  # был у этого врача
    assert c.get(f"/api/doctor/patients/{DANA}/history").status_code == 403  # к этому врачу не записана


def test_doctor_history(login):
    h = login("doctor.akhmetov").get(f"/api/doctor/patients/{DANA}/history").json()
    assert h["visits"][0]["icd_code"] == "I10" and len(h["tests"]) == 2
    assert h["visits"][0]["services_total"] == 13000


def _today_appt(c, fio="Иванов Сергей Петрович"):
    rows = c.get("/api/doctor/day", params={"on": TODAY.isoformat()}).json()
    return next(r["appointment"] for r in rows if r["appointment"] and r["appointment"]["patient_fio"] == fio)


def test_visit_validation(login):
    c = login("doctor.akhmetov")
    r = c.post(f"/api/doctor/appointments/{_today_appt(c)['appt_no']}/visit", json={"complaints": "", "icd_code": ""})
    assert r.status_code == 422 and {"complaints", "icd_code"} <= set(r.json()["detail"]["fields"])


def test_visit_full_cycle(login):
    """Приём → назначение медсестре → направление в лабораторию → результат виден пациенту."""
    c = login("doctor.akhmetov")
    a = _today_appt(c)
    r = c.post(f"/api/doctor/appointments/{a['appt_no']}/visit", json={
        "complaints": "Давящая боль за грудиной при подъёме", "icd_code": "I10", "conclusion": "ЭКГ, контроль АД",
        "prescriptions": [{"procedure_code": "P04", "sessions": 2, "instructions": "Утром"}],
        "referrals": [{"test_code": "T02"}],
        "services": [{"service_code": "S003", "qty": 1}, {"service_code": "S005", "qty": 1}]})
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["author"] == "doctor.akhmetov" and v["services_total"] == 13000
    assert c.get(f"/api/doctor/appointments/{a['appt_no']}").json()["status_code"] == "DONE"
    # повторно внести нельзя
    assert c.post(f"/api/doctor/appointments/{a['appt_no']}/visit",
                  json={"complaints": "x", "icd_code": "I10"}).status_code == 400

    rx_no = v["prescriptions"][0]["rx_no"]
    n = login("nurse.omarova")
    rows = n.get("/api/nurse/procedures", params={"on": TODAY.isoformat()}).json()
    assert any(r["prescription"]["rx_no"] == rx_no for r in rows)
    assert n.post(f"/api/nurse/prescriptions/{rx_no}/execute", json={"note": "130/85"}).status_code == 200
    assert n.post(f"/api/nurse/prescriptions/{rx_no}/execute", json={}).status_code == 200
    r = n.post(f"/api/nurse/prescriptions/{rx_no}/execute", json={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "SESSIONS_EXHAUSTED"

    ref_no = v["referrals"][0]["ref_no"]
    lab = login("lab.sadykova")
    assert any(x["ref_no"] == ref_no for x in lab.get("/api/lab/referrals").json())
    assert lab.post(f"/api/lab/referrals/{ref_no}/result", json={"value_text": ""}).status_code == 422
    assert lab.post(f"/api/lab/referrals/{ref_no}/result",
                    json={"value_text": "Холестерин 5,2 ммоль/л"}).status_code == 201
    assert lab.post(f"/api/lab/referrals/{ref_no}/result", json={"value_text": "x"}).status_code == 400

    p = login("patient.ivanov").get("/api/cabinet").json()
    assert any(t["value_text"] == "Холестерин 5,2 ммоль/л" for t in p["health"]["tests"])


def test_visit_edit_keeps_history(login):
    c = login("doctor.akhmetov")
    a = _today_appt(c)
    v = c.post(f"/api/doctor/appointments/{a['appt_no']}/visit",
               json={"complaints": "Боль", "icd_code": "I10"}).json()
    r = c.put(f"/api/doctor/visits/{v['visit_no']}", json={"complaints": "Боль", "icd_code": "M54.5"})
    assert r.status_code == 200
    ch = r.json()["changes"]
    assert ch == [{**ch[0], "field": "icd_code", "old_value": "I10", "new_value": "M54.5"}]
    # другой врач изменить не может
    assert login("doctor.seitkali").put(f"/api/doctor/visits/{v['visit_no']}",
                                        json={"complaints": "x", "icd_code": "I10"}).status_code == 403


def test_future_visit_rejected(login):
    c = login("doctor.akhmetov")
    future = next(a for a in login("operator.reg1").get("/api/appointments", params={"iin": DANA}).json()
                  if a["status_code"] == "PLANNED")
    c = login("doctor.akhmetov")
    r = c.post(f"/api/doctor/appointments/{future['appt_no']}/visit", json={"complaints": "x", "icd_code": "I10"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "TOO_EARLY"


def test_no_show_only_after_start(login, monkeypatch):
    c = login("doctor.akhmetov")
    a = _today_appt(c)
    assert c.post(f"/api/doctor/appointments/{a['appt_no']}/no-show").json()["detail"]["code"] == "TOO_EARLY"
    from datetime import datetime

    from app.core import clock
    monkeypatch.setattr(clock, "now", lambda: datetime(2026, 11, 16, 12, 40))
    r = c.post(f"/api/doctor/appointments/{a['appt_no']}/no-show")
    assert r.status_code == 200 and r.json()["status_code"] == "NO_SHOW"


# ------------------------------------------------------------------ пациент (С1–С3, Т12)
def test_patient_sees_only_own(login):
    c = login("patient.dana")
    data = c.get("/api/cabinet").json()
    assert {a["patient_iin"] for a in data["appointments"]} == {DANA}
    other = next(a for a in login("operator.reg1").get("/api/appointments", params={"iin": IVANOV}).json())
    c = login("patient.dana")
    assert c.get(f"/api/appointments/{other['appt_no']}").status_code == 403
    assert c.post(f"/api/appointments/{other['appt_no']}/cancel").status_code == 403
    assert c.get(f"/api/doctor/patients/{IVANOV}/history").status_code == 403


def test_patient_self_booking_and_reschedule(login):
    c = login("patient.dana")
    slot = free_slot(c, "D-001", TODAY + timedelta(days=1))
    r = c.post("/api/appointments", json={"iin": IVANOV, "slot_id": slot, "reason": "Кашель"})  # чужой ИИН игнорируется
    assert r.status_code == 201 and r.json()["appointment"]["patient_iin"] == DANA
    no = r.json()["appointment"]["appt_no"]
    new = free_slot(c, "D-001", TODAY + timedelta(days=2))
    r = c.post(f"/api/appointments/{no}/reschedule", json={"slot_id": new})
    assert r.status_code == 200 and r.json()["appointment"]["slot_id"] == new
    assert c.post(f"/api/appointments/{no}/cancel").status_code == 200


# ------------------------------------------------------------------ администратор
def test_admin_generates_schedule(login):
    c = login("admin.clinic")
    rules = next(x for x in c.get("/api/schedule/work-rules").json() if x["doctor"]["tab_no"] == "D-021")
    assert [r["weekday"] for r in rules["rules"]] == [0, 2, 4]
    r = c.put("/api/schedule/work-rules/D-021", json={"rules": [{"weekday": 1, "time_start": "09:00",
                                                              "time_end": "11:00"}]})
    assert r.status_code == 200
    start = TODAY + timedelta(days=20)  # за пределами уже сформированного расписания
    r = c.post("/api/schedule/generate", json={"tab_no": "D-021", "date_from": start.isoformat(),
                                                    "date_to": (start + timedelta(days=6)).isoformat()})
    assert r.json()["created"] == 4  # один вторник, 09:00–11:00 по 30 минут
    again = c.post("/api/schedule/generate", json={"tab_no": "D-021", "date_from": start.isoformat(),
                                                        "date_to": (start + timedelta(days=6)).isoformat()})
    assert again.json()["created"] == 0


def test_admin_reports(login):
    r = login("admin.clinic").get("/api/reports", params={"date_from": (TODAY - timedelta(days=10)).isoformat(),
                                                                "date_to": (TODAY + timedelta(days=5)).isoformat()})
    t = r.json()["totals"]
    assert t["done"] == 2 and t["no_show"] == 1 and t["revenue_kzt"] == 20000


def test_admin_only(login):
    assert login("operator.reg1").get("/api/reports").status_code == 403
