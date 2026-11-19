"""Автоматическая проверка функций ИС (ПР 6 – задание 5, СРО 12, СРО 15).

Запуск:  python3 tests.py
Каждый тест создаёт отдельную временную базу данных, поэтому рабочая база clinic.db не изменяется.
"""
import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta

TMP = tempfile.mkdtemp()
os.environ["CLINIC_DB"] = os.path.join(TMP, "test.db")
os.environ.setdefault("CLINIC_STAGE", "3")

import init_db  # noqa: E402
import app as clinic  # noqa: E402

DANA = "040512650123"     # есть действующая запись к кардиологу D-017
AIZHAN = "950302400789"


def free_slot(tab="D-017", days_ahead=3, skip=0):
    con = sqlite3.connect(os.environ["CLINIC_DB"])
    row = con.execute("""SELECT slot_id FROM schedule_slot WHERE tab_no=? AND is_busy=0 AND slot_date>=?
                         ORDER BY slot_date, time_start LIMIT 1 OFFSET ?""",
                      (tab, (date.today() + timedelta(days=days_ahead)).isoformat(), skip)).fetchone()
    con.close()
    return row[0]


def sql(query, args=()):
    con = sqlite3.connect(os.environ["CLINIC_DB"])
    rows = con.execute(query, args).fetchall()
    con.close()
    return rows


class Base(unittest.TestCase):
    def setUp(self):
        init_db.build(os.environ["CLINIC_DB"])
        clinic.app.config["TESTING"] = True
        self.c = clinic.app.test_client()

    def login(self, login, pwd):
        return self.c.post("/login", data={"login": login, "password": pwd}, follow_redirects=True)

    def text(self, resp):
        return resp.get_data(as_text=True)


class AppointmentFunction(Base):
    """ПР 6: функция «Запись пациента на приём» (форма «Запись на приём», алгоритм СРО 11)."""

    def setUp(self):
        super().setUp()
        self.login("operator.reg1", "oper123")

    def test_01_find_by_iin(self):
        t = self.text(self.c.get(f"/appointment/new?action=find&iin={AIZHAN}"))
        self.assertIn("Нурланова Айжан Маратовна", t)

    def test_02_iin_format(self):
        t = self.text(self.c.get("/appointment/new?action=find&iin=12345"))
        self.assertIn("ИИН должен содержать 12 цифр", t)

    def test_03_iin_not_found(self):
        t = self.text(self.c.get("/appointment/new?action=find&iin=999999999999"))
        self.assertIn("не найден", t)

    def test_04_schedule_shows_busy_and_free(self):
        sid = free_slot()
        day = sql("SELECT slot_date FROM schedule_slot WHERE slot_id=?", (sid,))[0][0]
        t = self.text(self.c.get(f"/appointment/new?pid={AIZHAN}&spec=CARD&doc=D-017&day={day}"))
        self.assertIn("свободен", t)

    def test_05_create_ok(self):
        sid = free_slot()
        before = sql("SELECT COUNT(*) FROM appointment")[0][0]
        r = self.c.post("/appointment/create", data={"pid": AIZHAN, "spec": "CARD", "doc": "D-017",
                                                     "slot": sid, "reason": "Одышка при нагрузке"},
                        follow_redirects=True)
        self.assertIn("Пациент записан", self.text(r))
        self.assertEqual(sql("SELECT COUNT(*) FROM appointment")[0][0], before + 1)
        self.assertEqual(sql("SELECT is_busy FROM schedule_slot WHERE slot_id=?", (sid,))[0][0], 1)
        self.assertEqual(sql("SELECT status_code FROM appointment WHERE slot_id=? AND iin=?", (sid, AIZHAN))[0][0],
                         "PLANNED")
        self.assertEqual(sql("SELECT COUNT(*) FROM sms_outbox")[0][0], 1)

    def test_06_reason_required(self):
        sid = free_slot()
        t = self.text(self.c.post("/appointment/create", data={"pid": AIZHAN, "doc": "D-017", "slot": sid,
                                                                "reason": "   "}))
        self.assertIn("Укажите причину обращения", t)
        self.assertEqual(sql("SELECT is_busy FROM schedule_slot WHERE slot_id=?", (sid,))[0][0], 0)

    def test_07_busy_slot_rejected(self):
        sid = sql("SELECT slot_id FROM appointment WHERE status_code='PLANNED' AND slot_id LIKE '%D017%'")[0][0]
        before = sql("SELECT COUNT(*) FROM appointment")[0][0]
        t = self.text(self.c.post("/appointment/create", data={"pid": AIZHAN, "doc": "D-017", "slot": sid,
                                                                "reason": "Проверка"}))
        self.assertIn("Интервал уже занят", t)
        self.assertEqual(sql("SELECT COUNT(*) FROM appointment")[0][0], before)

    def test_08_existing_appointment_warning(self):
        sid = free_slot(skip=2)
        t = self.text(self.c.post("/appointment/create", data={"pid": DANA, "doc": "D-017", "slot": sid,
                                                                "reason": "Контроль"}))
        self.assertIn("уже есть действующая запись", t)
        t = self.text(self.c.post("/appointment/create", data={"pid": DANA, "doc": "D-017", "slot": sid,
                                                                "reason": "Контроль", "confirm": "no"}))
        self.assertIn("Запись не создана, выполните перенос записи", t)
        self.assertEqual(sql("SELECT is_busy FROM schedule_slot WHERE slot_id=?", (sid,))[0][0], 0)
        r = self.c.post("/appointment/create", data={"pid": DANA, "doc": "D-017", "slot": sid,
                                                     "reason": "Контроль", "confirm": "yes"}, follow_redirects=True)
        self.assertIn("Пациент записан", self.text(r))

    def test_09_db_blocks_double_booking(self):
        """Т5 на уровне БД: второй записи на тот же интервал не допускает уникальный индекс."""
        sid = free_slot()
        con = sqlite3.connect(os.environ["CLINIC_DB"])
        con.execute("INSERT INTO appointment (appt_no,iin,slot_id,reason,created_by) VALUES ('Z-T-1',?,?,'a','operator.reg1')",
                    (AIZHAN, sid))
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO appointment (appt_no,iin,slot_id,reason,created_by) VALUES ('Z-T-2',?,?,'b','operator.reg1')",
                        ("880915300456", sid))
        con.close()

    def test_10_ticket_after_reopen(self):
        sid = free_slot()
        self.c.post("/appointment/create", data={"pid": AIZHAN, "doc": "D-017", "slot": sid, "reason": "Талон"})
        no = sql("SELECT appt_no FROM appointment WHERE slot_id=?", (sid,))[0][0]
        t = self.text(self.c.get(f"/appointment/{no}/ticket"))
        self.assertIn("ТАЛОН НА ПРИЁМ", t)
        self.assertIn("Ахметов Нурлан", t)

    def test_11_role_restriction(self):
        self.c.get("/logout")
        self.login("nurse.omarova", "nurse123")
        self.assertEqual(self.c.get("/appointment/new").status_code, 403)


class Stage2(Base):
    """СРО 12: регистрация пациента, список записей, отмена записи."""

    def setUp(self):
        super().setUp()
        self.login("operator.reg1", "oper123")

    def reg(self, **kw):
        data = {"iin": "990808400111", "last_name": "Касымова", "first_name": "Жанна", "middle_name": "",
                "birth_date": "1999-08-08", "sex": "Ж", "mobile_phone": "+7 701 000 11 22", "address": "",
                "doc_type": "Удостоверение личности", "doc_no": "051234567"}
        data.update(kw)
        return self.c.post("/patients/new", data=data, follow_redirects=True)

    def test_21_register_ok(self):
        self.assertIn("зарегистрирован", self.text(self.reg()))
        self.assertEqual(sql("SELECT last_name FROM patient WHERE iin='990808400111'")[0][0], "Касымова")

    def test_22_duplicate_iin(self):
        t = self.text(self.reg(iin=DANA))
        self.assertIn("уже существует", t)
        self.assertEqual(sql("SELECT COUNT(*) FROM patient WHERE iin=?", (DANA,))[0][0], 1)

    def test_23_required_fields(self):
        t = self.text(self.reg(last_name="", birth_date=""))
        self.assertIn("Укажите фамилию", t)
        self.assertEqual(sql("SELECT COUNT(*) FROM patient WHERE iin='990808400111'")[0][0], 0)

    def test_24_cancel_frees_slot(self):
        no, sid = sql("SELECT appt_no, slot_id FROM appointment WHERE status_code='PLANNED'")[0]
        self.c.post(f"/appointment/{no}/cancel", data={"back": "/appointments"})
        self.assertEqual(sql("SELECT status_code FROM appointment WHERE appt_no=?", (no,))[0][0], "CANCELLED")
        self.assertEqual(sql("SELECT is_busy FROM schedule_slot WHERE slot_id=?", (sid,))[0][0], 0)

    def test_25_cancel_done_forbidden(self):
        no = sql("SELECT appt_no FROM appointment WHERE status_code='DONE'")[0][0]
        r = self.c.post(f"/appointment/{no}/cancel", data={"back": "/appointments"}, follow_redirects=True)
        self.assertIn("только запись в состоянии", self.text(r))

    def test_26_new_patient_can_be_booked(self):
        self.reg()
        sid = free_slot("D-001")
        r = self.c.post("/appointment/create", data={"pid": "990808400111", "doc": "D-001", "slot": sid,
                                                     "reason": "Профосмотр"}, follow_redirects=True)
        self.assertIn("Пациент записан", self.text(r))


class Stage3(Base):
    """Итоговая версия: перенос, врач, медсестра, личный кабинет."""

    def test_31_reschedule(self):
        self.login("operator.reg1", "oper123")
        no, old = sql("SELECT appt_no, slot_id FROM appointment WHERE status_code='PLANNED' AND slot_id LIKE '%D017%'")[0]
        new = free_slot()
        self.c.post(f"/appointment/{no}/reschedule", data={"slot": new})
        self.assertEqual(sql("SELECT slot_id FROM appointment WHERE appt_no=?", (no,))[0][0], new)
        self.assertEqual(sql("SELECT is_busy FROM schedule_slot WHERE slot_id=?", (old,))[0][0], 0)
        self.assertEqual(sql("SELECT old_slot_id FROM appointment_history WHERE appt_no=? AND action='перенос'", (no,))[0][0], old)

    def test_32_reschedule_to_busy(self):
        self.login("operator.reg1", "oper123")
        rows = sql("SELECT appt_no, slot_id FROM appointment WHERE status_code='PLANNED' AND slot_id LIKE '%D017%' ORDER BY slot_id")
        (no, old), (_, busy) = rows[0], rows[1]
        r = self.c.post(f"/appointment/{no}/reschedule", data={"slot": busy}, follow_redirects=True)
        self.assertIn("исходная запись сохранена", self.text(r))
        self.assertEqual(sql("SELECT slot_id FROM appointment WHERE appt_no=?", (no,))[0][0], old)

    def test_33_doctor_visit(self):
        self.login("doctor.akhmetov", "doc123")
        no = sql("SELECT appt_no FROM appointment a JOIN schedule_slot s ON s.slot_id=a.slot_id "
                 "WHERE s.tab_no='D-017' AND a.status_code='PLANNED'")[0][0]
        t = self.text(self.c.post(f"/doctor/visit/{no}", data={"complaints": "", "icd_code": ""}))
        self.assertIn("Укажите жалобы", t)
        self.c.post(f"/doctor/visit/{no}", data={"complaints": "Сердцебиение", "icd_code": "I10",
                                                 "conclusion": "Контроль АД", "rx0_code": "P04",
                                                 "rx0_sessions": "3", "rx0_instr": "Утром"})
        self.assertEqual(sql("SELECT status_code FROM appointment WHERE appt_no=?", (no,))[0][0], "DONE")
        self.assertEqual(sql("SELECT author FROM visit WHERE appt_no=?", (no,))[0][0], "doctor.akhmetov")
        self.assertEqual(sql("SELECT COUNT(*) FROM prescription p JOIN visit v ON v.visit_no=p.visit_no WHERE v.appt_no=?",
                             (no,))[0][0], 1)

    def test_34_doctor_access_restriction(self):
        self.login("doctor.seitkali", "doc123")                                        # терапевт D-001
        self.assertEqual(self.c.get("/doctor/patient/880915300456").status_code, 200)  # был у этого врача
        self.assertEqual(self.c.get(f"/doctor/patient/{DANA}").status_code, 403)       # к этому врачу не записана

    def test_35_nurse_execution_limit(self):
        self.login("nurse.omarova", "nurse123")
        rx = sql("SELECT rx_no, sessions FROM prescription WHERE procedure_code='P01'")[0]
        self.c.post(f"/nurse/execute/{rx[0]}", data={"note": "без реакции"})
        self.assertEqual(sql("SELECT COUNT(*) FROM procedure_execution WHERE rx_no=?", (rx[0],))[0][0], 1)
        con = sqlite3.connect(os.environ["CLINIC_DB"])
        for _ in range(rx[1] - 1):
            con.execute("INSERT INTO procedure_execution (rx_no, executed_at, nurse_login) VALUES (?,?,?)",
                        (rx[0], "2026-01-01 10:00:00", "nurse.omarova"))
        con.commit(); con.close()
        r = self.c.post(f"/nurse/execute/{rx[0]}", data={}, follow_redirects=True)
        self.assertIn("уже выполнены", self.text(r))

    def test_36_patient_sees_only_own(self):
        self.login("patient.dana", "pat123")
        t = self.text(self.c.get("/cabinet"))
        self.assertIn("I10", t)
        self.assertNotIn("Иванов", t)
        other = sql("SELECT appt_no FROM appointment WHERE iin<>? AND status_code='PLANNED'", (DANA,))[0][0]
        self.assertEqual(self.c.post(f"/appointment/{other}/cancel").status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
