"""ИС медицинской клиники – программная реализация (Flask + SQLite).

Запуск:  python3 init_db.py   (один раз – создать базу)
         python3 app.py       (открыть http://127.0.0.1:5000)

CLINIC_STAGE задаёт состав реализованных функций по этапам проекта:
  1 – ПР 6: вход в систему и функция «Запись пациента на приём» (форма «Запись на приём»);
  2 – СРО 12: + регистрация и изменение данных пациента, список записей, отмена записи;
  3 – итоговая версия (СРО 15): + перенос записи, рабочие места врача, медсестры, личный кабинет пациента.
"""
import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CLINIC_DB", os.path.join(BASE, "clinic.db"))
STAGE = int(os.environ.get("CLINIC_STAGE", "3"))
VERSION = {1: "0.1 (ПР 6)", 2: "0.2 (СРО 12)", 3: "1.0 (СРО 15)"}[STAGE]

app = Flask(__name__)
app.secret_key = "clinic-is-demo-key"

ROLE_NAMES = {"OPERATOR": "Оператор регистратуры", "DOCTOR": "Врач-специалист",
              "NURSE": "Медицинская сестра", "PATIENT": "Пациент"}
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


# ----------------------------------------------------------------- база данных
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def q(sql, args=(), one=False):
    cur = db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def next_number(prefix, table, column):
    """Номер документа вида Z-2026-000001 (СРО 10, идентифицирующие данные)."""
    year = date.today().year
    row = q(f"SELECT MAX({column}) AS m FROM {table} WHERE {column} LIKE ?", (f"{prefix}-{year}-%",), one=True)
    last = int(row["m"].split("-")[-1]) if row and row["m"] else 0
    return f"{prefix}-{year}-{last + 1:06d}"


# ----------------------------------------------------------------- оформление
@app.template_filter("ru_date")
def ru_date(value, weekday=False):
    if not value:
        return ""
    d = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    text = f"{d.day} {MONTHS[d.month - 1]} {d.year}"
    return f"{text} ({WEEKDAYS[d.weekday()]})" if weekday else text


@app.template_filter("dmy")
def dmy(value):
    if not value:
        return ""
    s = str(value)
    d = date.fromisoformat(s[:10]).strftime("%d.%m.%Y")
    return d + (" " + s[11:16] if len(s) > 10 else "")


def fio(row, prefix=""):
    parts = [row[prefix + "last_name"], row[prefix + "first_name"], row[prefix + "middle_name"]]
    return " ".join(p for p in parts if p)


app.jinja_env.globals.update(fio=fio, STAGE=STAGE, VERSION=VERSION, ROLE_NAMES=ROLE_NAMES,
                             today=lambda: date.today().isoformat())


# ----------------------------------------------------------------- доступ (Т13)
def current_user():
    if "login" not in session:
        return None
    return q("SELECT * FROM user_account WHERE login=? AND is_active=1", (session["login"],), one=True)


@app.context_processor
def inject_user():
    return {"user": current_user()}


def role_required(*roles, stage=1):
    def deco(view):
        @wraps(view)
        def wrapper(*a, **kw):
            if STAGE < stage:
                abort(404)
            u = current_user()
            if not u:
                return redirect(url_for("login", next=request.path))
            if u["role_code"] not in roles:
                return render_template("denied.html"), 403
            return view(*a, **kw)
        return wrapper
    return deco


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = q("SELECT * FROM user_account WHERE login=?", (request.form.get("login", "").strip(),), one=True)
        if u and u["is_active"] and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session.clear()
            session["login"] = u["login"]
            return redirect(request.args.get("next") or url_for("index"))
        error = "Неверный логин или пароль"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    u = current_user()
    if not u:
        return redirect(url_for("login"))
    today = date.today().isoformat()
    stats = {}
    if u["role_code"] == "OPERATOR":
        stats["today"] = q("""SELECT COUNT(*) c FROM appointment a JOIN schedule_slot s ON s.slot_id=a.slot_id
                              WHERE s.slot_date=? AND a.status_code='PLANNED'""", (today,), one=True)["c"]
        stats["patients"] = q("SELECT COUNT(*) c FROM patient", one=True)["c"]
    if u["role_code"] == "DOCTOR":
        stats["today"] = q("""SELECT COUNT(*) c FROM appointment a JOIN schedule_slot s ON s.slot_id=a.slot_id
                              WHERE s.slot_date=? AND s.tab_no=? AND a.status_code='PLANNED'""",
                           (today, u["tab_no"]), one=True)["c"]
    return render_template("index.html", stats=stats)


# ============================================================ ФОРМА «ЗАПИСЬ НА ПРИЁМ»
def load_form_context(args):
    """Собирает данные формы «Запись на приём» по выбранным значениям (элементы 1–13 СРО 11)."""
    ctx = {"iin": args.get("iin", "").strip(), "pid": args.get("pid", ""), "spec": args.get("spec", ""),
           "doc": args.get("doc", ""), "day": args.get("day", ""), "slot": args.get("slot", ""),
           "reason": args.get("reason", ""), "fio_q": args.get("fio_q", "").strip(),
           "birth_q": args.get("birth_q", ""), "found": [], "patient": None, "candidate": None,
           "doctors": [], "doctor": None, "slots": [], "selected": None, "nearest": None,
           "messages": []}
    # Блок «Пациент»: поиск по ИИН (элементы 1–2) или по ФИО и дате рождения (элемент 3, А1).
    if args.get("action") == "find":
        if not (len(ctx["iin"]) == 12 and ctx["iin"].isdigit()):
            ctx["messages"].append(("error", "ИИН должен содержать 12 цифр"))                 # И2
        else:
            p = q("SELECT * FROM patient WHERE iin=?", (ctx["iin"],), one=True)
            if p:
                ctx["candidate"] = p
            else:
                msg = f"Пациент с ИИН {ctx['iin']} не найден. Необходимо зарегистрировать пациента."
                ctx["messages"].append(("warn", msg))                                         # И3
                ctx["offer_registration"] = True
    if args.get("action") == "find_fio":
        parts = ctx["fio_q"].split()
        if not parts or not ctx["birth_q"]:
            ctx["messages"].append(("error", "Для поиска укажите фамилию (ФИО) и дату рождения"))
        else:
            sql = "SELECT * FROM patient WHERE last_name LIKE ? AND birth_date=?"
            params = [parts[0] + "%", ctx["birth_q"]]
            if len(parts) > 1:
                sql += " AND first_name LIKE ?"
                params.append(parts[1] + "%")
            ctx["found"] = q(sql, params)
            if not ctx["found"]:
                ctx["messages"].append(("warn", "Карты с такими ФИО и датой рождения не найдены"))
    if ctx["pid"]:
        ctx["patient"] = q("SELECT * FROM patient WHERE iin=?", (ctx["pid"],), one=True)
    # Блок «Врач и дата приёма» (элементы 6–10).
    ctx["specialties"] = q("""SELECT * FROM ref_specialty WHERE is_active=1 AND specialty_code IN
                              (SELECT specialty_code FROM doctor WHERE is_active=1) ORDER BY name""")
    if ctx["spec"]:
        ctx["doctors"] = q("""SELECT * FROM doctor WHERE specialty_code=? AND is_active=1
                              ORDER BY last_name""", (ctx["spec"],))
    if ctx["doc"]:
        ctx["doctor"] = q("""SELECT d.*, s.name AS spec_name, s.visit_minutes, c.floor_no
                             FROM doctor d JOIN ref_specialty s ON s.specialty_code=d.specialty_code
                             JOIN ref_cabinet c ON c.cabinet_no=d.cabinet_no WHERE d.tab_no=?""",
                          (ctx["doc"],), one=True)
    if ctx["doctor"] and ctx["day"]:
        ctx["slots"] = q("""SELECT s.*, c.floor_no FROM schedule_slot s JOIN ref_cabinet c ON c.cabinet_no=s.cabinet_no
                            WHERE s.tab_no=? AND s.slot_date=? ORDER BY s.time_start""", (ctx["doc"], ctx["day"]))
        if not ctx["slots"]:
            ctx["messages"].append(("warn", f"Врач не принимает {ru_date(ctx['day'])}. Выберите другую дату "
                                             f"или нажмите «Ближайшие свободные»."))                # И4
        elif not any(is_bookable(s) for s in ctx["slots"]):
            ctx["messages"].append(("warn", "На выбранную дату свободных интервалов нет. "
                                             "Нажмите «Ближайшие свободные»."))                    # А2
    if ctx["doctor"] and args.get("near"):
        ctx["nearest"] = q("""SELECT slot_date, COUNT(*) AS free_count, MIN(time_start) AS first_time
                              FROM schedule_slot WHERE tab_no=? AND is_busy=0 AND
                              (slot_date > ? OR (slot_date = ? AND time_start > ?))
                              GROUP BY slot_date ORDER BY slot_date LIMIT 5""",
                           (ctx["doc"], date.today().isoformat(), date.today().isoformat(),
                            datetime.now().strftime("%H:%M")))
    if ctx["slot"]:
        ctx["selected"] = q("""SELECT s.*, c.floor_no FROM schedule_slot s JOIN ref_cabinet c ON c.cabinet_no=s.cabinet_no
                               WHERE s.slot_id=?""", (ctx["slot"],), one=True)
    return ctx


def is_bookable(slot):
    """Интервал можно выбрать: свободен и ещё не наступил."""
    start = datetime.fromisoformat(f"{slot['slot_date']}T{slot['time_start']}")
    return not slot["is_busy"] and start > datetime.now()


app.jinja_env.globals["is_bookable"] = is_bookable


@app.route("/appointment/new")
@role_required("OPERATOR")
def appointment_form():
    ctx = load_form_context(request.args)
    created = request.args.get("created")
    if created:
        ctx["created"] = appointment_details(created)
        ctx["messages"].append(("ok", "Пациент записан"))
    return render_template("appointment_form.html", **ctx)


def appointment_details(appt_no):
    return q("""SELECT a.*, st.name AS status_name, s.slot_date, s.time_start, s.time_end, s.cabinet_no, c.floor_no,
                       d.tab_no, d.last_name AS d_last_name, d.first_name AS d_first_name,
                       d.middle_name AS d_middle_name, sp.name AS spec_name,
                       p.last_name, p.first_name, p.middle_name, p.mobile_phone, p.birth_date
                FROM appointment a JOIN schedule_slot s ON s.slot_id=a.slot_id
                JOIN ref_appointment_status st ON st.status_code=a.status_code
                JOIN ref_cabinet c ON c.cabinet_no=s.cabinet_no
                JOIN doctor d ON d.tab_no=s.tab_no JOIN ref_specialty sp ON sp.specialty_code=d.specialty_code
                JOIN patient p ON p.iin=a.iin WHERE a.appt_no=?""", (appt_no,), one=True)


def send_sms(appt_no, action="запись"):
    """SMS-подтверждение (Т8). Шлюз не подключён – сообщение сохраняется в sms_outbox (имитация)."""
    a = appointment_details(appt_no)
    doctor = f"{a['d_last_name']} {a['d_first_name'][0]}.{(a['d_middle_name'] or ' ')[0]}."
    if action == "отмена":
        text = (f"Клиника: запись {a['appt_no']} к врачу {doctor} на {dmy(a['slot_date'])} "
                f"{a['time_start']} отменена.")
    else:
        verb = "перенесена" if action == "перенос" else "подтверждена"
        text = (f"Клиника: запись {verb}. {a['spec_name']} {doctor}, {dmy(a['slot_date'])} в {a['time_start']}, "
                f"каб. {a['cabinet_no']} ({a['floor_no']} этаж). Номер {a['appt_no']}.")
    db().execute("INSERT INTO sms_outbox (appt_no, phone, text) VALUES (?,?,?)", (appt_no, a["mobile_phone"], text))


@app.route("/appointment/create", methods=["POST"])
@role_required("OPERATOR")
def appointment_create():
    """Алгоритм регистрации записи на приём (СРО 11, блок-схема, блоки 1–12)."""
    f = request.form
    keep = {k: f.get(k, "") for k in ("pid", "spec", "doc", "day", "slot", "reason")}
    u = current_user()

    def back(kind, text, **extra):
        ctx = load_form_context({**keep, **extra})
        ctx["messages"].append((kind, text))
        return render_template("appointment_form.html", **ctx)

    # Блок 1: ввод данных записи. Проверка, что пациент и интервал выбраны.
    if not keep["pid"] or not q("SELECT 1 FROM patient WHERE iin=?", (keep["pid"],), one=True):
        return back("error", "Сначала найдите и подтвердите пациента")
    if not keep["slot"]:
        return back("error", "Выберите свободный интервал в расписании врача")
    # Блоки 2–3: причина обращения заполнена? (И5)
    if not keep["reason"].strip():
        return back("error", "Укажите причину обращения", reason_error=1)
    con = db()
    # Блоки 4–5: повторное чтение интервала из БД в момент сохранения (И6, Т5).
    s = q("SELECT * FROM schedule_slot WHERE slot_id=?", (keep["slot"],), one=True)
    if not s or not is_bookable(s):
        keep["slot"] = ""
        return back("error", "Интервал уже занят или время приёма прошло. Выберите другой интервал.")
    # Блоки 6–9: есть действующая запись пациента к этому врачу? (А4)
    existing = q("""SELECT a.appt_no, s.slot_date, s.time_start FROM appointment a
                    JOIN schedule_slot s ON s.slot_id=a.slot_id
                    WHERE a.iin=? AND s.tab_no=? AND a.status_code='PLANNED'
                    ORDER BY s.slot_date, s.time_start""", (keep["pid"], s["tab_no"]), one=True)
    if existing and f.get("confirm") != "yes":
        if f.get("confirm") == "no":
            return back("warn", "Запись не создана, выполните перенос записи")              # блок 9
        ctx = load_form_context(keep)
        ctx["confirm_existing"] = existing                                                   # блок 7
        return render_template("appointment_form.html", **ctx)
    # Блок 10: регистрация записи и отметка интервала занятым – в одной транзакции.
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute("UPDATE schedule_slot SET is_busy=1 WHERE slot_id=? AND is_busy=0", (s["slot_id"],))
        if cur.rowcount != 1:            # интервал заняли одновременно другим пользователем
            con.rollback()
            keep["slot"] = ""
            return back("error", "Интервал уже занят. Расписание обновлено, выберите другой интервал.")
        appt_no = next_number("Z", "appointment", "appt_no")
        con.execute("""INSERT INTO appointment (appt_no, iin, slot_id, reason, status_code, created_by)
                       VALUES (?,?,?,?, 'PLANNED', ?)""", (appt_no, keep["pid"], s["slot_id"],
                                                          keep["reason"].strip(), u["login"]))
        con.execute("""INSERT INTO appointment_history (appt_no, action, new_slot_id, new_status, changed_by)
                       VALUES (?, 'создание', ?, 'PLANNED', ?)""", (appt_no, s["slot_id"], u["login"]))
        send_sms(appt_no)                                                                    # блок 11
        con.commit()
    except sqlite3.IntegrityError:
        con.rollback()
        keep["slot"] = ""
        return back("error", "Интервал уже занят. Выберите другой интервал.")
    # Блок 12: сообщение «Пациент записан».
    return redirect(url_for("appointment_form", pid=keep["pid"], spec=keep["spec"], doc=keep["doc"],
                            day=keep["day"], created=appt_no))


@app.route("/appointment/<appt_no>/ticket")
@role_required("OPERATOR", "PATIENT")
def appointment_ticket(appt_no):
    a = appointment_details(appt_no)
    if not a:
        abort(404)
    u = current_user()
    if u["role_code"] == "PATIENT" and a["iin"] != u["iin"]:
        return render_template("denied.html"), 403
    return render_template("ticket.html", a=a)


@app.route("/sms")
@role_required("OPERATOR")
def sms_log():
    rows = q("SELECT * FROM sms_outbox ORDER BY id DESC LIMIT 50")
    return render_template("sms.html", rows=rows)


# ============================================================ ЭТАП 2 (СРО 12)
PATIENT_FIELDS = ("iin", "last_name", "first_name", "middle_name", "birth_date", "sex",
                  "mobile_phone", "address", "doc_type", "doc_no")


def validate_patient(data, new=True):
    errors = {}
    if new:
        if not (len(data["iin"]) == 12 and data["iin"].isdigit()):
            errors["iin"] = "ИИН должен содержать 12 цифр"
        elif q("SELECT 1 FROM patient WHERE iin=?", (data["iin"],), one=True):
            errors["iin"] = "Карта с таким ИИН уже существует"
    for key, name in (("last_name", "фамилию"), ("first_name", "имя"), ("birth_date", "дату рождения"),
                      ("mobile_phone", "мобильный телефон")):
        if not data[key].strip():
            errors[key] = f"Укажите {name}"
    if data["birth_date"]:
        try:
            if date.fromisoformat(data["birth_date"]) > date.today():
                errors["birth_date"] = "Дата рождения не может быть позже текущей даты"
        except ValueError:
            errors["birth_date"] = "Неверный формат даты"
    phone_digits = "".join(ch for ch in data["mobile_phone"] if ch.isdigit())
    if data["mobile_phone"].strip() and len(phone_digits) != 11:
        errors["mobile_phone"] = "Телефон должен содержать 11 цифр, например +7 701 234 56 78"
    return errors


@app.route("/patients/new", methods=["GET", "POST"])
@role_required("OPERATOR", stage=2)
def patient_new():
    data = {k: request.values.get(k, "").strip() for k in PATIENT_FIELDS}
    errors, existing = {}, None
    if request.method == "POST":
        errors = validate_patient(data)
        if errors.get("iin") == "Карта с таким ИИН уже существует":                          # Т1
            existing = q("SELECT * FROM patient WHERE iin=?", (data["iin"],), one=True)
        if not errors:
            db().execute(f"""INSERT INTO patient ({",".join(PATIENT_FIELDS)}) VALUES ({",".join("?" * len(PATIENT_FIELDS))})""",
                         [data[k] or None for k in PATIENT_FIELDS])
            db().commit()
            flash(f"Пациент {data['last_name']} {data['first_name']} зарегистрирован. Электронная карта создана.")
            return redirect(url_for("patient_edit", iin=data["iin"]))
    return render_template("patient_form.html", data=data, errors=errors, existing=existing, new=True)


@app.route("/patients/<iin>", methods=["GET", "POST"])
@role_required("OPERATOR", stage=2)
def patient_edit(iin):
    p = q("SELECT * FROM patient WHERE iin=?", (iin,), one=True)
    if not p:
        abort(404)
    data = dict(p)
    errors = {}
    if request.method == "POST":
        for k in PATIENT_FIELDS[1:]:
            data[k] = request.form.get(k, "").strip()
        errors = validate_patient(data, new=False)
        if not errors:
            db().execute(f"""UPDATE patient SET {",".join(k + "=?" for k in PATIENT_FIELDS[1:])} WHERE iin=?""",
                         [data[k] or None for k in PATIENT_FIELDS[1:]] + [iin])
            db().commit()
            flash("Изменения сохранены")
            return redirect(url_for("patient_edit", iin=iin))
    appts = q("""SELECT a.*, st.name AS status_name, s.slot_date, s.time_start, s.cabinet_no,
                        d.last_name AS d_last_name, d.first_name AS d_first_name, d.middle_name AS d_middle_name
                 FROM appointment a JOIN schedule_slot s ON s.slot_id=a.slot_id
                 JOIN ref_appointment_status st ON st.status_code=a.status_code JOIN doctor d ON d.tab_no=s.tab_no
                 WHERE a.iin=? ORDER BY s.slot_date DESC, s.time_start DESC""", (iin,))
    return render_template("patient_form.html", data=data, errors=errors, new=False, appts=appts)


@app.route("/appointments")
@role_required("OPERATOR", stage=2)
def appointments_list():
    flt = {"day": request.args.get("day", date.today().isoformat()), "doc": request.args.get("doc", ""),
           "iin": request.args.get("iin", "").strip(), "status": request.args.get("status", "")}
    sql = """SELECT a.*, st.name AS status_name, s.slot_date, s.time_start, s.cabinet_no,
                    p.last_name, p.first_name, p.middle_name, d.last_name AS d_last_name,
                    d.first_name AS d_first_name, d.middle_name AS d_middle_name, sp.name AS spec_name
             FROM appointment a JOIN schedule_slot s ON s.slot_id=a.slot_id
             JOIN ref_appointment_status st ON st.status_code=a.status_code
             JOIN patient p ON p.iin=a.iin JOIN doctor d ON d.tab_no=s.tab_no
             JOIN ref_specialty sp ON sp.specialty_code=d.specialty_code WHERE 1=1"""
    args = []
    if flt["iin"]:
        sql += " AND a.iin=?"
        args.append(flt["iin"])
    elif flt["day"]:
        sql += " AND s.slot_date=?"
        args.append(flt["day"])
    if flt["doc"]:
        sql += " AND s.tab_no=?"
        args.append(flt["doc"])
    if flt["status"]:
        sql += " AND a.status_code=?"
        args.append(flt["status"])
    rows = q(sql + " ORDER BY s.slot_date, s.time_start", args)
    doctors = q("""SELECT d.*, s.name AS spec_name FROM doctor d JOIN ref_specialty s
                   ON s.specialty_code=d.specialty_code ORDER BY d.last_name""")
    statuses = q("SELECT * FROM ref_appointment_status")
    return render_template("appointments.html", rows=rows, flt=flt, doctors=doctors, statuses=statuses)


def cancel_appointment(appt_no, login):
    """Отмена записи (Т6.2): только в состоянии «Запланирована», интервал освобождается."""
    con = db()
    a = q("SELECT * FROM appointment WHERE appt_no=?", (appt_no,), one=True)
    if not a:
        return False, "Запись не найдена"
    if a["status_code"] != "PLANNED":
        return False, "Отменить можно только запись в состоянии «Запланирована»"
    con.execute("UPDATE appointment SET status_code='CANCELLED' WHERE appt_no=?", (appt_no,))
    con.execute("UPDATE schedule_slot SET is_busy=0 WHERE slot_id=?", (a["slot_id"],))
    con.execute("""INSERT INTO appointment_history (appt_no, action, old_slot_id, old_status, new_status, changed_by)
                   VALUES (?, 'отмена', ?, 'PLANNED', 'CANCELLED', ?)""", (appt_no, a["slot_id"], login))
    send_sms(appt_no, "отмена")
    con.commit()
    return True, f"Запись {appt_no} отменена, интервал освобождён"


@app.route("/appointment/<appt_no>/cancel", methods=["POST"])
@role_required("OPERATOR", "PATIENT", stage=2)
def appointment_cancel(appt_no):
    u = current_user()
    a = q("SELECT * FROM appointment WHERE appt_no=?", (appt_no,), one=True)
    if not a:
        abort(404)
    if u["role_code"] == "PATIENT" and a["iin"] != u["iin"]:
        return render_template("denied.html"), 403
    ok, msg = cancel_appointment(appt_no, u["login"])
    flash(msg, "ok" if ok else "error")
    return redirect(request.form.get("back") or url_for("index"))


# ============================================================ ЭТАП 3 (итоговая версия)
@app.route("/appointment/<appt_no>/reschedule", methods=["GET", "POST"])
@role_required("OPERATOR", stage=3)
def appointment_reschedule(appt_no):
    """Перенос записи (Т6.1): новый интервал проверяется, прежний освобождается, история сохраняется (Т7)."""
    a = appointment_details(appt_no)
    if not a:
        abort(404)
    day = request.values.get("day", a["slot_date"])
    con = db()
    if request.method == "POST":
        new_slot = request.form.get("slot", "")
        s = q("SELECT * FROM schedule_slot WHERE slot_id=? AND tab_no=?", (new_slot, a["tab_no"]), one=True)
        if a["status_code"] != "PLANNED":
            flash("Перенести можно только запись в состоянии «Запланирована»", "error")
        elif not s or not is_bookable(s):
            flash("Новый интервал занят. Перенос не выполнен, исходная запись сохранена.", "error")
        else:
            con.execute("BEGIN IMMEDIATE")
            cur = con.execute("UPDATE schedule_slot SET is_busy=1 WHERE slot_id=? AND is_busy=0", (new_slot,))
            if cur.rowcount != 1:
                con.rollback()
                flash("Новый интервал занят. Перенос не выполнен, исходная запись сохранена.", "error")
            else:
                con.execute("UPDATE schedule_slot SET is_busy=0 WHERE slot_id=?", (a["slot_id"],))
                con.execute("UPDATE appointment SET slot_id=? WHERE appt_no=?", (new_slot, appt_no))
                con.execute("""INSERT INTO appointment_history (appt_no, action, old_slot_id, new_slot_id, old_status,
                               new_status, changed_by) VALUES (?, 'перенос', ?, ?, 'PLANNED', 'PLANNED', ?)""",
                            (appt_no, a["slot_id"], new_slot, current_user()["login"]))
                send_sms(appt_no, "перенос")
                con.commit()
                flash(f"Запись {appt_no} перенесена. Прежний интервал освобождён, SMS для пациента сформировано.", "ok")
                return redirect(url_for("appointments_list", iin=a["iin"]))
    slots = q("SELECT * FROM schedule_slot WHERE tab_no=? AND slot_date=? ORDER BY time_start", (a["tab_no"], day))
    history = q("""SELECT h.*, o.slot_date AS old_date, o.time_start AS old_time, n.slot_date AS new_date,
                          n.time_start AS new_time FROM appointment_history h
                   LEFT JOIN schedule_slot o ON o.slot_id=h.old_slot_id LEFT JOIN schedule_slot n ON n.slot_id=h.new_slot_id
                   WHERE h.appt_no=? ORDER BY h.id""", (appt_no,))
    return render_template("reschedule.html", a=a, day=day, slots=slots, history=history)


# ---------------- Врач-специалист
def doctor_can_see(tab_no, iin):
    """Т13: врачу доступны карты пациентов, записанных на приём к этому врачу."""
    return q("""SELECT 1 FROM appointment a JOIN schedule_slot s ON s.slot_id=a.slot_id
                WHERE a.iin=? AND s.tab_no=?""", (iin, tab_no), one=True) is not None


@app.route("/doctor/day")
@role_required("DOCTOR", stage=3)
def doctor_day():
    u = current_user()
    day = request.args.get("day", date.today().isoformat())
    rows = q("""SELECT s.*, a.appt_no, a.reason, a.status_code, st.name AS status_name, p.iin,
                       p.last_name, p.first_name, p.middle_name, p.birth_date
                FROM schedule_slot s LEFT JOIN appointment a ON a.slot_id=s.slot_id AND a.status_code<>'CANCELLED'
                LEFT JOIN ref_appointment_status st ON st.status_code=a.status_code
                LEFT JOIN patient p ON p.iin=a.iin
                WHERE s.tab_no=? AND s.slot_date=? ORDER BY s.time_start""", (u["tab_no"], day))
    return render_template("doctor_day.html", rows=rows, day=day)


def patient_history(iin, tab_no=None):
    visits = q("""SELECT v.*, dg.name AS diag_name, s.slot_date, d.last_name AS d_last_name,
                         d.first_name AS d_first_name, d.middle_name AS d_middle_name, sp.name AS spec_name
                  FROM visit v JOIN appointment a ON a.appt_no=v.appt_no JOIN schedule_slot s ON s.slot_id=a.slot_id
                  JOIN doctor d ON d.tab_no=s.tab_no JOIN ref_specialty sp ON sp.specialty_code=d.specialty_code
                  JOIN ref_diagnosis dg ON dg.icd_code=v.icd_code WHERE a.iin=? ORDER BY v.finished_at DESC""", (iin,))
    rx = q("""SELECT r.*, pt.name AS proc_name, v.finished_at,
                     (SELECT COUNT(*) FROM procedure_execution e WHERE e.rx_no=r.rx_no) AS done_count
              FROM prescription r JOIN visit v ON v.visit_no=r.visit_no JOIN appointment a ON a.appt_no=v.appt_no
              JOIN ref_procedure_type pt ON pt.procedure_code=r.procedure_code WHERE a.iin=?
              ORDER BY r.created_at DESC""", (iin,))
    tests = q("""SELECT t.*, tt.name AS test_name FROM test_result t JOIN ref_test_type tt ON tt.test_code=t.test_code
                 WHERE t.iin=? ORDER BY t.done_date DESC""", (iin,))
    return visits, rx, tests


@app.route("/doctor/patient/<iin>")
@role_required("DOCTOR", stage=3)
def doctor_patient(iin):
    u = current_user()
    if not doctor_can_see(u["tab_no"], iin):
        return render_template("denied.html"), 403
    p = q("SELECT * FROM patient WHERE iin=?", (iin,), one=True)
    visits, rx, tests = patient_history(iin)
    return render_template("doctor_patient.html", p=p, visits=visits, rx=rx, tests=tests,
                           appt=request.args.get("appt"))


@app.route("/doctor/visit/<appt_no>", methods=["GET", "POST"])
@role_required("DOCTOR", stage=3)
def doctor_visit(appt_no):
    """Фиксация результатов приёма и оформление назначений (Т10)."""
    u = current_user()
    a = appointment_details(appt_no)
    if not a or a["tab_no"] != u["tab_no"]:
        return render_template("denied.html"), 403
    diagnoses = q("SELECT * FROM ref_diagnosis ORDER BY icd_code")
    procedures = q("SELECT * FROM ref_procedure_type ORDER BY procedure_code")
    form = {k: request.form.get(k, "") for k in ("complaints", "icd_code", "conclusion")}
    rx_rows = [{"code": request.form.get(f"rx{i}_code", ""), "sessions": request.form.get(f"rx{i}_sessions", ""),
                "instr": request.form.get(f"rx{i}_instr", "")} for i in range(3)]
    errors = {}
    if request.method == "POST":
        if a["status_code"] != "PLANNED":
            errors["general"] = "Результаты можно внести только по записи в состоянии «Запланирована»"
        if not form["complaints"].strip():
            errors["complaints"] = "Укажите жалобы пациента"
        if not form["icd_code"]:
            errors["icd_code"] = "Выберите основной диагноз из справочника МКБ-10"
        for i, r in enumerate(rx_rows):
            if r["code"] and not (r["sessions"].isdigit() and 1 <= int(r["sessions"]) <= 30):
                errors[f"rx{i}"] = "Количество сеансов – от 1 до 30"
        if not errors:
            con = db()
            visit_no = next_number("P", "visit", "visit_no")
            con.execute("""INSERT INTO visit (visit_no, appt_no, complaints, icd_code, conclusion, author)
                           VALUES (?,?,?,?,?,?)""", (visit_no, appt_no, form["complaints"].strip(),
                                                    form["icd_code"], form["conclusion"].strip(), u["login"]))
            for r in rx_rows:
                if r["code"]:
                    con.execute("""INSERT INTO prescription (rx_no, visit_no, procedure_code, sessions, instructions,
                                   start_date, author) VALUES (?,?,?,?,?,?,?)""",
                                (next_number("N", "prescription", "rx_no"), visit_no, r["code"], int(r["sessions"]),
                                 r["instr"].strip(), date.today().isoformat(), u["login"]))
            con.execute("UPDATE appointment SET status_code='DONE' WHERE appt_no=?", (appt_no,))
            con.execute("""INSERT INTO appointment_history (appt_no, action, old_status, new_status, changed_by)
                           VALUES (?, 'приём проведён', 'PLANNED', 'DONE', ?)""", (appt_no, u["login"]))
            con.commit()
            flash(f"Результаты приёма сохранены ({visit_no}). Запись переведена в состояние «Проведена».", "ok")
            return redirect(url_for("doctor_day", day=a["slot_date"]))
    return render_template("doctor_visit.html", a=a, diagnoses=diagnoses, procedures=procedures,
                           form=form, rx_rows=rx_rows, errors=errors)


@app.route("/doctor/noshow/<appt_no>", methods=["POST"])
@role_required("DOCTOR", stage=3)
def doctor_noshow(appt_no):
    u = current_user()
    a = appointment_details(appt_no)
    if not a or a["tab_no"] != u["tab_no"]:
        return render_template("denied.html"), 403
    if a["status_code"] == "PLANNED":
        db().execute("UPDATE appointment SET status_code='NO_SHOW' WHERE appt_no=?", (appt_no,))
        db().execute("""INSERT INTO appointment_history (appt_no, action, old_status, new_status, changed_by)
                        VALUES (?, 'неявка', 'PLANNED', 'NO_SHOW', ?)""", (appt_no, u["login"]))
        db().commit()
        flash(f"Отмечена неявка пациента по записи {appt_no}", "ok")
    return redirect(url_for("doctor_day", day=a["slot_date"]))


# ---------------- Медицинская сестра
@app.route("/nurse/procedures")
@role_required("NURSE", stage=3)
def nurse_procedures():
    day = request.args.get("day", date.today().isoformat())
    rows = q("""SELECT r.*, pt.name AS proc_name, pt.cabinet_no, p.iin, p.last_name, p.first_name, p.middle_name,
                       d.last_name AS d_last_name, d.first_name AS d_first_name, d.middle_name AS d_middle_name,
                       (SELECT COUNT(*) FROM procedure_execution e WHERE e.rx_no=r.rx_no) AS done_count,
                       (SELECT COUNT(*) FROM procedure_execution e WHERE e.rx_no=r.rx_no
                         AND date(e.executed_at)=?) AS done_today
                FROM prescription r JOIN ref_procedure_type pt ON pt.procedure_code=r.procedure_code
                JOIN visit v ON v.visit_no=r.visit_no JOIN appointment a ON a.appt_no=v.appt_no
                JOIN patient p ON p.iin=a.iin JOIN schedule_slot s ON s.slot_id=a.slot_id JOIN doctor d ON d.tab_no=s.tab_no
                WHERE r.start_date<=? AND ((SELECT COUNT(*) FROM procedure_execution e WHERE e.rx_no=r.rx_no
                         AND date(e.executed_at)<?) < r.sessions)
                ORDER BY pt.cabinet_no, p.last_name""", (day, day, day))
    return render_template("nurse.html", rows=rows, day=day)


@app.route("/nurse/execute/<rx_no>", methods=["POST"])
@role_required("NURSE", stage=3)
def nurse_execute(rx_no):
    """Фиксация выполнения процедуры (Т11.2): только по назначению врача, пока сеансы не исчерпаны."""
    r = q("""SELECT r.*, (SELECT COUNT(*) FROM procedure_execution e WHERE e.rx_no=r.rx_no) AS done_count
             FROM prescription r WHERE r.rx_no=?""", (rx_no,), one=True)
    day = request.form.get("day", date.today().isoformat())
    if not r:
        flash("Назначение не найдено – отметка без назначения врача не допускается", "error")
    elif r["done_count"] >= r["sessions"]:
        flash(f"Все сеансы по назначению {rx_no} уже выполнены", "error")
    else:
        db().execute("INSERT INTO procedure_execution (rx_no, executed_at, nurse_login, note) VALUES (?,?,?,?)",
                     (rx_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), current_user()["login"],
                      request.form.get("note", "").strip() or None))
        db().commit()
        flash(f"Выполнение процедуры по назначению {rx_no} отмечено (сеанс {r['done_count'] + 1} из {r['sessions']})", "ok")
    return redirect(url_for("nurse_procedures", day=day))


# ---------------- Личный кабинет пациента
@app.route("/cabinet")
@role_required("PATIENT", stage=3)
def patient_cabinet():
    u = current_user()
    p = q("SELECT * FROM patient WHERE iin=?", (u["iin"],), one=True)
    appts = q("""SELECT a.*, st.name AS status_name, s.slot_date, s.time_start, s.cabinet_no,
                        d.last_name AS d_last_name, d.first_name AS d_first_name, d.middle_name AS d_middle_name,
                        sp.name AS spec_name
                 FROM appointment a JOIN schedule_slot s ON s.slot_id=a.slot_id
                 JOIN ref_appointment_status st ON st.status_code=a.status_code JOIN doctor d ON d.tab_no=s.tab_no
                 JOIN ref_specialty sp ON sp.specialty_code=d.specialty_code
                 WHERE a.iin=? ORDER BY s.slot_date DESC, s.time_start DESC""", (u["iin"],))
    visits, rx, tests = patient_history(u["iin"])
    return render_template("cabinet.html", p=p, appts=appts, visits=visits, rx=rx, tests=tests)


@app.errorhandler(404)
def not_found(_e):
    return render_template("denied.html", not_found=True), 404


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        import init_db
        init_db.build(DB_PATH)
    app.run(debug=False, port=int(os.environ.get("PORT", "5000")))
