-- ИС медицинской клиники. Структура базы данных (SQLite).
-- Справочники ref_* перенесены из СРО 10 (clinic_ref.sql) без изменения состава полей.
PRAGMA foreign_keys = ON;

-- ===================== СПРАВОЧНИКИ (СРО 10) =====================
CREATE TABLE ref_specialty (
    specialty_code TEXT PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    visit_minutes  INTEGER NOT NULL CHECK (visit_minutes BETWEEN 10 AND 120),
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE ref_cabinet (
    cabinet_no TEXT PRIMARY KEY,
    floor_no   INTEGER NOT NULL,
    purpose    TEXT NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE ref_appointment_status (
    status_code   TEXT PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    occupies_slot INTEGER NOT NULL CHECK (occupies_slot IN (0, 1))
);

CREATE TABLE ref_role (
    role_code TEXT PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    rights    TEXT NOT NULL
);

CREATE TABLE ref_diagnosis (
    icd_code TEXT PRIMARY KEY,
    name     TEXT NOT NULL
);

CREATE TABLE ref_procedure_type (
    procedure_code TEXT PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    minutes        INTEGER NOT NULL,
    cabinet_no     TEXT REFERENCES ref_cabinet(cabinet_no)
);

CREATE TABLE ref_service (
    service_code   TEXT PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    specialty_code TEXT REFERENCES ref_specialty(specialty_code),
    price_kzt      REAL NOT NULL CHECK (price_kzt > 0),
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE ref_test_type (
    test_code  TEXT PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    test_group TEXT NOT NULL CHECK (test_group IN ('лабораторное', 'инструментальное')),
    ready_days INTEGER NOT NULL
);

-- ===================== ОСНОВНЫЕ ОБЪЕКТЫ (СРО 10) =====================
-- Пациент. Идентификатор – ИИН (Т1, Т3). Поля документа добавлены по Т3 (несоответствие, выявленное в СРО 12).
CREATE TABLE patient (
    iin          TEXT PRIMARY KEY CHECK (length(iin) = 12 AND iin NOT GLOB '*[^0-9]*'),
    last_name    TEXT NOT NULL CHECK (trim(last_name) <> ''),
    first_name   TEXT NOT NULL CHECK (trim(first_name) <> ''),
    middle_name  TEXT,
    birth_date   TEXT NOT NULL,              -- ГГГГ-ММ-ДД
    sex          TEXT CHECK (sex IN ('М', 'Ж')),
    mobile_phone TEXT NOT NULL,
    address      TEXT,
    doc_type     TEXT,                       -- вид документа (Т3)
    doc_no       TEXT,                       -- номер документа (Т3)
    reg_date     TEXT NOT NULL DEFAULT (date('now', 'localtime'))
);

-- Врач. Идентификатор – табельный номер.
CREATE TABLE doctor (
    tab_no         TEXT PRIMARY KEY,
    last_name      TEXT NOT NULL,
    first_name     TEXT NOT NULL,
    middle_name    TEXT,
    specialty_code TEXT NOT NULL REFERENCES ref_specialty(specialty_code),
    cabinet_no     TEXT NOT NULL REFERENCES ref_cabinet(cabinet_no),
    work_phone     TEXT,
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

-- Интервал расписания. Существует только в рабочее время врача.
CREATE TABLE schedule_slot (
    slot_id    TEXT PRIMARY KEY,                       -- R-ГГГГММДД-табномер-NN
    tab_no     TEXT NOT NULL REFERENCES doctor(tab_no),
    slot_date  TEXT NOT NULL,                          -- ГГГГ-ММ-ДД
    time_start TEXT NOT NULL,                          -- ЧЧ:ММ
    time_end   TEXT NOT NULL,
    cabinet_no TEXT NOT NULL REFERENCES ref_cabinet(cabinet_no),
    is_busy    INTEGER NOT NULL DEFAULT 0 CHECK (is_busy IN (0, 1)),
    UNIQUE (tab_no, slot_date, time_start),
    CHECK (time_end > time_start)
);

-- Учётная запись (Т13). display_name добавлено для медсестёр и операторов (нет отдельного объекта «Сотрудник»).
CREATE TABLE user_account (
    login         TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role_code     TEXT NOT NULL REFERENCES ref_role(role_code),
    display_name  TEXT NOT NULL,
    tab_no        TEXT REFERENCES doctor(tab_no),      -- для роли DOCTOR
    iin           TEXT REFERENCES patient(iin),        -- для роли PATIENT
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

-- Запись на приём (Т5, Т7). Врач, дата, время и кабинет определяются через интервал.
CREATE TABLE appointment (
    appt_no     TEXT PRIMARY KEY,                      -- Z-ГГГГ-NNNNNN
    iin         TEXT NOT NULL REFERENCES patient(iin),
    slot_id     TEXT NOT NULL REFERENCES schedule_slot(slot_id),
    reason      TEXT NOT NULL CHECK (trim(reason) <> ''),
    status_code TEXT NOT NULL DEFAULT 'PLANNED' REFERENCES ref_appointment_status(status_code),
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    created_by  TEXT NOT NULL REFERENCES user_account(login)
);
-- Защита от наложения записей на уровне БД: на один интервал – только одна запись,
-- занимающая интервал (PLANNED, DONE, NO_SHOW). Отменённые записи интервал не занимают (Т5, Т6.2).
CREATE UNIQUE INDEX ux_appointment_active_slot
    ON appointment(slot_id) WHERE status_code IN ('PLANNED', 'DONE', 'NO_SHOW');

-- История изменений записи (Т7: прежние дата и время сохраняются при переносе).
CREATE TABLE appointment_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    appt_no     TEXT NOT NULL REFERENCES appointment(appt_no),
    action      TEXT NOT NULL,                         -- создание / перенос / отмена / неявка / приём проведён
    old_slot_id TEXT,
    new_slot_id TEXT,
    old_status  TEXT,
    new_status  TEXT,
    changed_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    changed_by  TEXT NOT NULL
);

-- Приём (посещение): результаты приёма (Т10).
CREATE TABLE visit (
    visit_no    TEXT PRIMARY KEY,                      -- P-ГГГГ-NNNNNN
    appt_no     TEXT NOT NULL UNIQUE REFERENCES appointment(appt_no),
    complaints  TEXT NOT NULL,
    icd_code    TEXT NOT NULL REFERENCES ref_diagnosis(icd_code),
    conclusion  TEXT,
    finished_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    author      TEXT NOT NULL                          -- логин врача (Т10)
);

-- Назначение процедуры (Т10, Т11.1).
CREATE TABLE prescription (
    rx_no          TEXT PRIMARY KEY,                   -- N-ГГГГ-NNNNNN
    visit_no       TEXT NOT NULL REFERENCES visit(visit_no),
    procedure_code TEXT NOT NULL REFERENCES ref_procedure_type(procedure_code),
    sessions       INTEGER NOT NULL CHECK (sessions BETWEEN 1 AND 30),
    instructions   TEXT,
    start_date     TEXT NOT NULL,                      -- с какой даты выполнять
    created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    author         TEXT NOT NULL
);

-- Выполнение процедуры (Т11.2). Отдельная таблица: у назначения может быть несколько сеансов.
CREATE TABLE procedure_execution (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rx_no       TEXT NOT NULL REFERENCES prescription(rx_no),
    executed_at TEXT NOT NULL,
    nurse_login TEXT NOT NULL REFERENCES user_account(login),
    note        TEXT
);

-- Оказанная услуга (структура подготовлена, функция учёта пока не реализована).
CREATE TABLE rendered_service (
    line_no      TEXT PRIMARY KEY,
    visit_no     TEXT NOT NULL REFERENCES visit(visit_no),
    service_code TEXT NOT NULL REFERENCES ref_service(service_code),
    qty          INTEGER NOT NULL DEFAULT 1 CHECK (qty > 0),
    price_kzt    REAL NOT NULL
);

-- Результат исследования (Т9, Т12). Вносится тестовым скриптом – порядок внесения не определён (СРО 7).
CREATE TABLE test_result (
    result_no  TEXT PRIMARY KEY,
    iin        TEXT NOT NULL REFERENCES patient(iin),
    test_code  TEXT NOT NULL REFERENCES ref_test_type(test_code),
    tab_no     TEXT REFERENCES doctor(tab_no),
    done_date  TEXT NOT NULL,
    value_text TEXT NOT NULL
);

-- Исходящие SMS-подтверждения (Т8). Шлюз SMS не подключён: сообщение сохраняется как отправленное в режиме имитации.
CREATE TABLE sms_outbox (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    appt_no    TEXT NOT NULL REFERENCES appointment(appt_no),
    phone      TEXT NOT NULL,
    text       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    status     TEXT NOT NULL DEFAULT 'имитация отправки'
);
