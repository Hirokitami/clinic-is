"""Создание базы данных clinic.db и заполнение тестовыми записями.

Запуск:  python3 init_db.py
Расписание врачей формируется на 14 дней вперёд от текущей даты,
поэтому демонстрация работает в любой день.
"""
import os
import sqlite3
from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CLINIC_DB", os.path.join(BASE, "clinic.db"))

REF_SQL = """
INSERT INTO ref_specialty VALUES
 ('THER','Терапевт',20,1),('CARD','Кардиолог',30,1),('NEUR','Невролог',30,1),
 ('ENT','Оториноларинголог',20,1),('OPHT','Офтальмолог',20,1),('SURG','Хирург',30,1),
 ('GYN','Гинеколог',30,1);
INSERT INTO ref_cabinet VALUES
 ('101',1,'Регистратура',1),('105',1,'Процедурный кабинет',1),('108',1,'Лаборатория (забор анализов)',1),
 ('201',2,'Кабинет терапевта',1),('203',2,'Кабинет кардиолога',1),('204',2,'Кабинет ЭКГ',1),
 ('206',2,'Кабинет невролога',1),('301',3,'Кабинет хирурга',1),('302',3,'Кабинет УЗИ',1);
INSERT INTO ref_appointment_status VALUES
 ('PLANNED','Запланирована',1),('DONE','Проведена',1),('CANCELLED','Отменена',0),('NO_SHOW','Неявка',1);
INSERT INTO ref_role VALUES
 ('PATIENT','Пациент','Своя запись: просмотр, отмена; просмотр своих результатов и назначений'),
 ('OPERATOR','Оператор регистратуры','Регистрация пациентов, запись, перенос и отмена записей'),
 ('DOCTOR','Врач-специалист','Своё расписание, карты своих пациентов, диагнозы, назначения'),
 ('NURSE','Медицинская сестра','Перечень процедур на день, отметка о выполнении процедуры');
INSERT INTO ref_diagnosis VALUES
 ('I10','Эссенциальная (первичная) гипертензия'),
 ('J06.9','Острая инфекция верхних дыхательных путей неуточнённая'),
 ('K29.7','Гастрит неуточнённый'),('M54.5','Боль внизу спины'),
 ('E11.9','Сахарный диабет 2 типа без осложнений'),('J20.9','Острый бронхит неуточнённый');
INSERT INTO ref_procedure_type VALUES
 ('P01','Внутримышечная инъекция',10,'105'),('P02','Внутривенная капельная инфузия',60,'105'),
 ('P03','Перевязка',20,'105'),('P04','Измерение артериального давления',10,'105'),
 ('P05','Забор крови из вены',10,'108');
INSERT INTO ref_service VALUES
 ('S001','Первичный приём терапевта','THER',7000,1),('S002','Повторный приём терапевта','THER',5000,1),
 ('S003','Консультация кардиолога','CARD',9000,1),('S004','Консультация невролога','NEUR',9000,1),
 ('S005','Электрокардиография (ЭКГ)',NULL,4000,1),('S006','УЗИ органов брюшной полости',NULL,10000,1),
 ('S007','Общий анализ крови',NULL,2500,1),('S008','Внутримышечная инъекция',NULL,1500,1);
INSERT INTO ref_test_type VALUES
 ('T01','Общий анализ крови','лабораторное',1),('T02','Биохимический анализ крови','лабораторное',2),
 ('T03','Общий анализ мочи','лабораторное',1),('T04','Глюкоза крови','лабораторное',1),
 ('T05','Электрокардиография','инструментальное',0),('T06','УЗИ органов брюшной полости','инструментальное',0);
"""

DOCTORS = [
    # tab_no, фамилия, имя, отчество, специальность, кабинет, телефон
    ("D-001", "Сейткали", "Айгерим", "Болатовна", "THER", "201", "+7 727 250 10 01"),
    ("D-002", "Петров", "Олег", "Игоревич", "THER", "201", "+7 727 250 10 02"),
    ("D-017", "Ахметов", "Нурлан", "Серикович", "CARD", "203", "+7 727 250 10 17"),
    ("D-021", "Ким", "Елена", "Викторовна", "NEUR", "206", "+7 727 250 10 21"),
    ("D-030", "Жумабеков", "Ерлан", "Маратович", "SURG", "301", "+7 727 250 10 30"),
]

# Рабочее время: (дни недели 0=Пн, начало, конец)
WORK = {
    "D-001": ((0, 1, 2, 3, 4, 5), "09:00", "13:00"),
    "D-002": ((0, 1, 2, 3, 4), "14:00", "18:00"),
    "D-017": ((0, 1, 2, 3, 4), "09:00", "13:00"),
    "D-021": ((0, 2, 4), "14:00", "17:00"),      # Пн, Ср, Пт
    "D-030": ((1, 3), "10:00", "13:00"),         # Вт, Чт
}

PATIENTS = [
    ("040512650123", "Ахметова", "Дана", "Ерлановна", "2004-05-12", "Ж", "+7 701 234 56 78",
     "г. Алматы, ул. Сатпаева, 22", "Удостоверение личности", "054812377"),
    ("880915300456", "Иванов", "Сергей", "Петрович", "1988-09-15", "М", "+7 705 111 22 33",
     "г. Алматы, мкр. Аксай-4, д. 15", "Удостоверение личности", "041122905"),
    ("950302400789", "Нурланова", "Айжан", "Маратовна", "1995-03-02", "Ж", "+7 707 555 44 11",
     None, "Удостоверение личности", "047730118"),
    ("710623300321", "Беккалиев", "Марат", "Кайратович", "1971-06-23", "М", "+7 702 987 65 43",
     "г. Алматы, пр. Абая, 120", "Паспорт РК", "N12345678"),
    ("010101500654", "Смагулова", "Алия", None, "2001-01-01", "Ж", "+7 747 300 20 10",
     None, None, None),
]

USERS = [
    # login, пароль, роль, отображаемое имя, tab_no, iin
    ("operator.reg1", "oper123", "OPERATOR", "Байжанова Динара (регистратура)", None, None),
    ("doctor.akhmetov", "doc123", "DOCTOR", "Ахметов Н. С. (кардиолог)", "D-017", None),
    ("doctor.seitkali", "doc123", "DOCTOR", "Сейткали А. Б. (терапевт)", "D-001", None),
    ("nurse.omarova", "nurse123", "NURSE", "Омарова Гульнара (процедурный кабинет)", None, None),
    ("patient.dana", "pat123", "PATIENT", "Ахметова Дана Ерлановна", None, "040512650123"),
]


def t2m(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m


def m2t(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def build(db_path=DB_PATH, today=None):
    today = today or date.today()
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        con.executescript(f.read())
    con.executescript(REF_SQL)

    con.executemany("INSERT INTO doctor VALUES (?,?,?,?,?,?,?,1)", DOCTORS)
    for p in PATIENTS:
        con.execute("""INSERT INTO patient (iin,last_name,first_name,middle_name,birth_date,sex,
                       mobile_phone,address,doc_type,doc_no,reg_date) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (*p, (today - timedelta(days=200)).isoformat()))
    for login, pwd, role, name, tab, iin in USERS:
        con.execute("INSERT INTO user_account VALUES (?,?,?,?,?,?,1)",
                    (login, generate_password_hash(pwd), role, name, tab, iin))

    # Расписание: 10 дней назад (для истории) и 14 дней вперёд.
    minutes = dict(con.execute("SELECT specialty_code, visit_minutes FROM ref_specialty"))
    for tab, _, _, _, spec, cab, _ in DOCTORS:
        days, start, end = WORK[tab]
        step = minutes[spec]
        for shift in range(-10, 15):
            d = today + timedelta(days=shift)
            if d.weekday() not in days:
                continue
            n, m = 1, t2m(start)
            while m + step <= t2m(end):
                sid = f"R-{d:%Y%m%d}-{tab.replace('-', '')}-{n:02d}"
                con.execute("INSERT INTO schedule_slot VALUES (?,?,?,?,?,?,0)",
                            (sid, tab, d.isoformat(), m2t(m), m2t(m + step), cab))
                n += 1
                m += step

    # Тестовые записи на приём.
    seq = {"Z": 0, "P": 0, "N": 0}

    def next_no(prefix):
        seq[prefix] += 1
        return f"{prefix}-{today.year}-{seq[prefix]:06d}"

    def slot(tab, d, idx):
        sid = f"R-{d:%Y%m%d}-{tab.replace('-', '')}-{idx:02d}"
        row = con.execute("SELECT slot_id FROM schedule_slot WHERE slot_id=?", (sid,)).fetchone()
        return row[0] if row else None

    def work_day(tab, base, forward=True):
        days = WORK[tab][0]
        d = base
        while d.weekday() not in days:
            d += timedelta(days=1 if forward else -1)
        return d

    def book(iin, sid, reason, status="PLANNED", by="operator.reg1", created=None):
        no = next_no("Z")
        created = created or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        con.execute("INSERT INTO appointment VALUES (?,?,?,?,?,?,?)",
                    (no, iin, sid, reason, status, created, by))
        occupies = con.execute("SELECT occupies_slot FROM ref_appointment_status WHERE status_code=?",
                               (status,)).fetchone()[0]
        if occupies:
            con.execute("UPDATE schedule_slot SET is_busy=1 WHERE slot_id=?", (sid,))
        con.execute("""INSERT INTO appointment_history (appt_no,action,new_slot_id,new_status,changed_at,changed_by)
                       VALUES (?,?,?,?,?,?)""", (no, "создание", sid, status, created, by))
        return no

    # Прошедшие приёмы для истории пациента.
    past = work_day("D-017", today - timedelta(days=7), forward=False)
    a1 = book("040512650123", slot("D-017", past, 2), "Повышенное давление, головная боль", "DONE",
              created=f"{(past - timedelta(days=2)).isoformat()} 10:15:00")
    v1 = next_no("P")
    con.execute("INSERT INTO visit VALUES (?,?,?,?,?,?,?)",
                (v1, a1, "Головная боль по утрам, АД до 150/95", "I10",
                 "Рекомендован контроль АД 2 раза в день, ЭКГ, ОАК", f"{past.isoformat()} 09:58:00",
                 "doctor.akhmetov"))
    con.execute("INSERT INTO prescription VALUES (?,?,?,?,?,?,?,?)",
                (next_no("N"), v1, "P04", 5, "Измерять АД утром, результат вносить в отметку",
                 past.isoformat(), f"{past.isoformat()} 09:58:00", "doctor.akhmetov"))
    con.execute("INSERT INTO test_result VALUES (?,?,?,?,?,?)",
                ("L-2026-007712", "040512650123", "T01", "D-017", (past + timedelta(days=1)).isoformat(),
                 "Гемоглобин 128 г/л, лейкоциты 6,1×10⁹/л, СОЭ 8 мм/ч – в пределах нормы"))
    con.execute("INSERT INTO test_result VALUES (?,?,?,?,?,?)",
                ("L-2026-007713", "040512650123", "T05", "D-017", past.isoformat(),
                 "Синусовый ритм, ЧСС 78 уд/мин, признаков ишемии нет"))

    past2 = work_day("D-001", today - timedelta(days=4), forward=False)
    a2 = book("880915300456", slot("D-001", past2, 3), "Кашель, температура 37,8", "DONE",
              created=f"{(past2 - timedelta(days=1)).isoformat()} 16:40:00")
    v2 = next_no("P")
    con.execute("INSERT INTO visit VALUES (?,?,?,?,?,?,?)",
                (v2, a2, "Кашель 4 дня, субфебрильная температура", "J20.9",
                 "Обильное питьё, контроль через 7 дней", f"{past2.isoformat()} 09:55:00",
                 "doctor.seitkali"))
    con.execute("INSERT INTO prescription VALUES (?,?,?,?,?,?,?,?)",
                (next_no("N"), v2, "P01", 5, "Цефтриаксон 1,0 в/м 1 раз в день",
                 past2.isoformat(), f"{past2.isoformat()} 09:55:00", "doctor.seitkali"))

    # Будущие записи (занятые интервалы).
    d17 = work_day("D-017", today + timedelta(days=2))
    book("710623300321", slot("D-017", d17, 1), "Боль в груди при нагрузке")
    book("040512650123", slot("D-017", d17, 3), "Контроль давления после лечения")
    d01 = work_day("D-001", today + timedelta(days=1))
    book("950302400789", slot("D-001", d01, 2), "Насморк, боль в горле")
    book("710623300321", slot("D-001", d01, 5), "Справка для бассейна")
    # Приёмы врача на сегодня (если сегодня рабочий день кардиолога).
    if today.weekday() in WORK["D-017"][0]:
        book("010101500654", slot("D-017", today, 6), "Учащённое сердцебиение")
        book("880915300456", slot("D-017", today, 7), "Боль в груди при нагрузке")

    con.commit()
    con.close()
    return db_path


if __name__ == "__main__":
    path = build()
    print("База данных создана:", path)
