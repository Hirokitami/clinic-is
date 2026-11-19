"""Создание БД, справочники (СРО 10) и демонстрационные данные.

Запуск:  python -m app.seed        (пересоздаёт все таблицы!)
Расписание формируется на 10 дней назад и 14 дней вперёд от текущей даты,
поэтому демонстрация работает в любой день.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .core.db import Base, engine as default_engine
from .core.numbering import next_number
from .core.security import hash_password
from .modules import load_models
from .modules.appointments.models import Appointment, AppointmentHistory
from .modules.auth.models import Role, UserAccount
from .modules.lab.models import Referral, TestResult
from .modules.patients.models import Patient
from .modules.procedures.models import Prescription
from .modules.references.models import (AppointmentStatus, Cabinet, Diagnosis, ProcedureType, Service, Specialty,
                                        TestType)
from .modules.schedule import service as schedule
from .modules.schedule.models import Doctor, DoctorWorkRule, ScheduleSlot
from .modules.visits.models import RenderedService, Visit

load_models()

SPECIALTIES = [("THER", "Терапевт", 20), ("CARD", "Кардиолог", 30), ("NEUR", "Невролог", 30),
               ("ENT", "Оториноларинголог", 20), ("OPHT", "Офтальмолог", 20), ("SURG", "Хирург", 30),
               ("GYN", "Гинеколог", 30)]
CABINETS = [("101", 1, "Регистратура"), ("105", 1, "Процедурный кабинет"), ("108", 1, "Лаборатория (забор анализов)"),
            ("201", 2, "Кабинет терапевта"), ("203", 2, "Кабинет кардиолога"), ("204", 2, "Кабинет ЭКГ"),
            ("206", 2, "Кабинет невролога"), ("301", 3, "Кабинет хирурга"), ("302", 3, "Кабинет УЗИ")]
STATUSES = [("PLANNED", "Запланирована", True), ("DONE", "Проведена", True), ("CANCELLED", "Отменена", False),
            ("NO_SHOW", "Неявка", True)]
ROLES = [
    ("PATIENT", "Пациент", "Своя запись: запись, перенос, отмена; просмотр своих результатов и назначений"),
    ("OPERATOR", "Оператор регистратуры", "Регистрация пациентов, запись, перенос и отмена записей"),
    ("DOCTOR", "Врач-специалист", "Своё расписание, карты своих пациентов, диагнозы, назначения, направления, услуги"),
    ("NURSE", "Медицинская сестра", "Перечень процедур на день, отметка о выполнении процедуры"),
    ("LAB", "Сотрудник лаборатории", "Направления на исследования, внесение результатов"),
    ("ADMIN", "Администратор клиники", "Рабочее время врачей, формирование расписания, отчёты"),
]
DIAGNOSES = [("I10", "Эссенциальная (первичная) гипертензия"),
             ("J06.9", "Острая инфекция верхних дыхательных путей неуточнённая"),
             ("K29.7", "Гастрит неуточнённый"), ("M54.5", "Боль внизу спины"),
             ("E11.9", "Сахарный диабет 2 типа без осложнений"), ("J20.9", "Острый бронхит неуточнённый")]
PROCEDURES = [("P01", "Внутримышечная инъекция", 10, "105"), ("P02", "Внутривенная капельная инфузия", 60, "105"),
              ("P03", "Перевязка", 20, "105"), ("P04", "Измерение артериального давления", 10, "105"),
              ("P05", "Забор крови из вены", 10, "108")]
SERVICES = [("S001", "Первичный приём терапевта", "THER", 7000), ("S002", "Повторный приём терапевта", "THER", 5000),
            ("S003", "Консультация кардиолога", "CARD", 9000), ("S004", "Консультация невролога", "NEUR", 9000),
            ("S005", "Электрокардиография (ЭКГ)", None, 4000), ("S006", "УЗИ органов брюшной полости", None, 10000),
            ("S007", "Общий анализ крови", None, 2500), ("S008", "Внутримышечная инъекция", None, 1500)]
TEST_TYPES = [("T01", "Общий анализ крови", "лабораторное", 1), ("T02", "Биохимический анализ крови", "лабораторное", 2),
              ("T03", "Общий анализ мочи", "лабораторное", 1), ("T04", "Глюкоза крови", "лабораторное", 1),
              ("T05", "Электрокардиография", "инструментальное", 0),
              ("T06", "УЗИ органов брюшной полости", "инструментальное", 0)]

DOCTORS = [
    ("D-001", "Сейткали", "Айгерим", "Болатовна", "THER", "201", "+7 727 250 10 01"),
    ("D-002", "Петров", "Олег", "Игоревич", "THER", "201", "+7 727 250 10 02"),
    ("D-017", "Ахметов", "Нурлан", "Серикович", "CARD", "203", "+7 727 250 10 17"),
    ("D-021", "Ким", "Елена", "Викторовна", "NEUR", "206", "+7 727 250 10 21"),
    ("D-030", "Жумабеков", "Ерлан", "Маратович", "SURG", "301", "+7 727 250 10 30"),
]
WORK = {  # дни недели (0 = Пн), начало, конец
    "D-001": ((0, 1, 2, 3, 4, 5), "09:00", "13:00"),
    "D-002": ((0, 1, 2, 3, 4), "14:00", "18:00"),
    "D-017": ((0, 1, 2, 3, 4), "09:00", "13:00"),
    "D-021": ((0, 2, 4), "14:00", "17:00"),
    "D-030": ((1, 3), "10:00", "13:00"),
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
    ("010101500654", "Смагулова", "Алия", None, "2001-01-01", "Ж", "+7 747 300 20 10", None, None, None),
]
USERS = [  # login, пароль, роль, отображаемое имя, tab_no, iin
    ("operator.reg1", "oper123", "OPERATOR", "Байжанова Динара (регистратура)", None, None),
    ("doctor.akhmetov", "doc123", "DOCTOR", "Ахметов Н. С. (кардиолог)", "D-017", None),
    ("doctor.seitkali", "doc123", "DOCTOR", "Сейткали А. Б. (терапевт)", "D-001", None),
    ("nurse.omarova", "nurse123", "NURSE", "Омарова Гульнара (процедурный кабинет)", None, None),
    ("lab.sadykova", "lab123", "LAB", "Садыкова Жанар (лаборатория)", None, None),
    ("admin.clinic", "admin123", "ADMIN", "Мусин Арман (администратор клиники)", None, None),
    ("patient.dana", "pat123", "PATIENT", "Ахметова Дана Ерлановна", None, "040512650123"),
    ("patient.ivanov", "pat123", "PATIENT", "Иванов Сергей Петрович", None, "880915300456"),
]


def _t(s: str) -> time:
    return time.fromisoformat(s)


def seed_refs(db: Session) -> None:
    db.add_all(Specialty(specialty_code=c, name=n, visit_minutes=m) for c, n, m in SPECIALTIES)
    db.add_all(Cabinet(cabinet_no=c, floor_no=f, purpose=p) for c, f, p in CABINETS)
    db.add_all(AppointmentStatus(status_code=c, name=n, occupies_slot=o) for c, n, o in STATUSES)
    db.add_all(Role(role_code=c, name=n, rights=r) for c, n, r in ROLES)
    db.add_all(Diagnosis(icd_code=c, name=n) for c, n in DIAGNOSES)
    db.flush()
    db.add_all(ProcedureType(procedure_code=c, name=n, minutes=m, cabinet_no=cab) for c, n, m, cab in PROCEDURES)
    db.add_all(Service(service_code=c, name=n, specialty_code=s, price_kzt=p) for c, n, s, p in SERVICES)
    db.add_all(TestType(test_code=c, name=n, test_group=g, ready_days=d) for c, n, g, d in TEST_TYPES)
    db.flush()


def seed_demo(db: Session, today: date) -> None:
    db.add_all(Doctor(tab_no=t, last_name=l, first_name=f, middle_name=m, specialty_code=s, cabinet_no=c,
                      work_phone=ph) for t, l, f, m, s, c, ph in DOCTORS)
    for iin, l, f, m, b, sex, ph, addr, dt, dn in PATIENTS:
        db.add(Patient(iin=iin, last_name=l, first_name=f, middle_name=m, birth_date=date.fromisoformat(b), sex=sex,
                       mobile_phone=ph, address=addr, doc_type=dt, doc_no=dn, reg_date=today - timedelta(days=200)))
    db.flush()
    for login, pwd, role, name, tab, iin in USERS:
        db.add(UserAccount(login=login, password_hash=hash_password(pwd), role_code=role, display_name=name,
                           tab_no=tab, iin=iin))
    for tab, (days, start, end) in WORK.items():
        for wd in days:
            db.add(DoctorWorkRule(tab_no=tab, weekday=wd, time_start=_t(start), time_end=_t(end)))
    db.flush()
    for d in db.scalars(select(Doctor)):
        schedule.generate(db, d, today - timedelta(days=10), today + timedelta(days=14))
    db.flush()

    def work_day(tab: str, base: date, forward: bool = True) -> date:
        d = base
        while d.weekday() not in WORK[tab][0]:
            d += timedelta(days=1 if forward else -1)
        return d

    def slot(tab: str, d: date, idx: int) -> str:
        return schedule.slot_id_for(tab, d, idx)

    def book(iin: str, sid: str, reason: str, status: str = "PLANNED", created: datetime | None = None) -> str:
        created = created or datetime.now().replace(microsecond=0)
        no = next_number(db, "Z", today)
        db.add(Appointment(appt_no=no, iin=iin, slot_id=sid, reason=reason, status_code=status,
                           created_at=created, created_by="operator.reg1"))
        db.get(ScheduleSlot, sid).is_busy = status != "CANCELLED"
        db.add(AppointmentHistory(appt_no=no, action="создание", new_slot_id=sid, new_status=status,
                                  changed_at=created, changed_by="operator.reg1"))
        db.flush()
        return no

    def visit(appt_no: str, d: date, complaints: str, icd: str, conclusion: str, author: str, hour: str) -> str:
        no = next_number(db, "P", today)
        db.add(Visit(visit_no=no, appt_no=appt_no, complaints=complaints, icd_code=icd, conclusion=conclusion,
                     finished_at=datetime.combine(d, _t(hour)), author=author))
        db.flush()
        return no

    # Прошедшие приёмы – история пациента.
    past = work_day("D-017", today - timedelta(days=7), forward=False)
    a1 = book("040512650123", slot("D-017", past, 2), "Повышенное давление, головная боль", "DONE",
              datetime.combine(past - timedelta(days=2), _t("10:15")))
    v1 = visit(a1, past, "Головная боль по утрам, АД до 150/95", "I10",
               "Рекомендован контроль АД 2 раза в день, ЭКГ, ОАК", "doctor.akhmetov", "09:58")
    db.add(Prescription(rx_no=next_number(db, "N", today), visit_no=v1, procedure_code="P04", sessions=5,
                        instructions="Измерять АД утром, результат вносить в отметку", start_date=past,
                        created_at=datetime.combine(past, _t("09:58")), author="doctor.akhmetov"))
    r1 = next_number(db, "D", today)
    r2 = next_number(db, "D", today)
    db.add_all([
        Referral(ref_no=r1, visit_no=v1, test_code="T01", status="DONE", author="doctor.akhmetov",
                 created_at=datetime.combine(past, _t("09:58"))),
        Referral(ref_no=r2, visit_no=v1, test_code="T05", status="DONE", author="doctor.akhmetov",
                 created_at=datetime.combine(past, _t("09:58"))),
    ])
    db.add_all([RenderedService(line_no=next_number(db, "U", today), visit_no=v1, service_code="S003", qty=1,
                                price_kzt=9000),
                RenderedService(line_no=next_number(db, "U", today), visit_no=v1, service_code="S005", qty=1,
                                price_kzt=4000)])
    db.flush()
    db.add_all([
        TestResult(result_no=next_number(db, "L", today), iin="040512650123", test_code="T01", tab_no="D-017",
                   referral_no=r1, done_date=past + timedelta(days=1), entered_by="lab.sadykova",
                   value_text="Гемоглобин 128 г/л, лейкоциты 6,1×10⁹/л, СОЭ 8 мм/ч – в пределах нормы"),
        TestResult(result_no=next_number(db, "L", today), iin="040512650123", test_code="T05", tab_no="D-017",
                   referral_no=r2, done_date=past, entered_by="lab.sadykova",
                   value_text="Синусовый ритм, ЧСС 78 уд/мин, признаков ишемии нет"),
    ])

    past2 = work_day("D-001", today - timedelta(days=4), forward=False)
    a2 = book("880915300456", slot("D-001", past2, 3), "Кашель, температура 37,8", "DONE",
              datetime.combine(past2 - timedelta(days=1), _t("16:40")))
    v2 = visit(a2, past2, "Кашель 4 дня, субфебрильная температура", "J20.9",
               "Обильное питьё, контроль через 7 дней", "doctor.seitkali", "09:55")
    db.add(Prescription(rx_no=next_number(db, "N", today), visit_no=v2, procedure_code="P01", sessions=5,
                        instructions="Цефтриаксон 1,0 в/м 1 раз в день", start_date=past2,
                        created_at=datetime.combine(past2, _t("09:55")), author="doctor.seitkali"))
    db.add(Referral(ref_no=next_number(db, "D", today), visit_no=v2, test_code="T01", status="ORDERED",
                    note="Контроль воспалительных показателей", author="doctor.seitkali",
                    created_at=datetime.combine(past2, _t("09:55"))))
    db.add(RenderedService(line_no=next_number(db, "U", today), visit_no=v2, service_code="S001", qty=1,
                           price_kzt=7000))

    past3 = work_day("D-017", today - timedelta(days=3), forward=False)
    book("950302400789", slot("D-017", past3, 4), "Перебои в работе сердца", "NO_SHOW",
         datetime.combine(past3 - timedelta(days=1), _t("11:00")))

    # Будущие записи (занятые интервалы).
    d17 = work_day("D-017", today + timedelta(days=2))
    book("710623300321", slot("D-017", d17, 1), "Боль в груди при нагрузке")
    book("040512650123", slot("D-017", d17, 3), "Контроль давления после лечения")
    d01 = work_day("D-001", today + timedelta(days=1))
    book("950302400789", slot("D-001", d01, 2), "Насморк, боль в горле")
    book("710623300321", slot("D-001", d01, 5), "Справка для бассейна")
    # Приёмы кардиолога на сегодня (если сегодня его рабочий день).
    if today.weekday() in WORK["D-017"][0]:
        book("010101500654", slot("D-017", today, 6), "Учащённое сердцебиение")
        book("880915300456", slot("D-017", today, 7), "Боль в груди при нагрузке")


def build(eng: Engine | None = None, today: date | None = None, demo: bool = True) -> None:
    eng = eng or default_engine
    today = today or date.today()
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    with Session(eng) as db:
        seed_refs(db)
        if demo:
            seed_demo(db, today)
        db.commit()


def is_empty(eng: Engine | None = None) -> bool:
    eng = eng or default_engine
    from sqlalchemy import inspect
    if not inspect(eng).has_table("user_account"):
        return True
    with Session(eng) as db:
        return db.scalar(select(UserAccount.login).limit(1)) is None


if __name__ == "__main__":
    import sys

    if "--if-empty" in sys.argv and not is_empty():
        print("База данных уже заполнена – загрузка демо-данных пропущена.")
    else:
        build()
        print("База данных создана, демонстрационные данные загружены.")
