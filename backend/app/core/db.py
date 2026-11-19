from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 15}
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _sqlite_pragmas(dbapi_con, _rec):
            # Транзакцией управляет SQLAlchemy; BEGIN IMMEDIATE даёт блокировку записи
            # с начала транзакции – две одновременные записи на интервал выполняются по очереди.
            dbapi_con.isolation_level = None
            cur = dbapi_con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("PRAGMA journal_mode = WAL")
            cur.close()

        @event.listens_for(eng, "begin")
        def _sqlite_begin(conn):
            conn.exec_driver_sql("BEGIN IMMEDIATE")
    return eng


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
