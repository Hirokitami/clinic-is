"""Тестовое окружение: отдельная БД SQLite, часы клиники зафиксированы (понедельник, 08:00)."""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app import seed
from app.core.db import get_db, make_engine
from app.main import app
from app.core import clock, security

TODAY = date(2026, 11, 16)  # понедельник: работают кардиолог D-017 и терапевты
NOW = datetime(2026, 11, 16, 8, 0)

PASSWORDS = {"operator.reg1": "oper123", "doctor.akhmetov": "doc123", "doctor.seitkali": "doc123",
             "nurse.omarova": "nurse123", "patient.dana": "pat123", "patient.ivanov": "pat123",
             "lab.sadykova": "lab123", "admin.clinic": "admin123"}


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    monkeypatch.setattr(security, "_ITER", 1000)  # быстрые хэши паролей в тестах
    monkeypatch.setattr(clock, "now", lambda: NOW)
    eng = make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    seed.build(eng, today=TODAY)
    yield eng
    eng.dispose()


@pytest.fixture()
def Session(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def client(Session):
    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def login(client):
    """login("operator.reg1") → клиент с cookie этого пользователя."""

    def _login(user: str):
        client.cookies.clear()
        r = client.post("/api/auth/login", json={"login": user, "password": PASSWORDS[user]})
        assert r.status_code == 200, r.text
        return client

    return _login


def free_slot(client, tab_no: str, on: date, skip: int = 0) -> str:
    r = client.get(f"/api/schedule/{tab_no}", params={"on": on.isoformat()})
    assert r.status_code == 200, r.text
    free = [s["slot_id"] for s in r.json()["slots"] if s["bookable"]]
    return free[skip]
