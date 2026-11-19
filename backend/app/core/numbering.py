"""Номера документов вида Z-2026-000001 (СРО 10, идентифицирующие данные)."""
from datetime import date

from sqlalchemy import Integer, String, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base

# Z – запись на приём, P – приём, N – назначение, U – оказанная услуга, D – направление,
# L – результат исследования.


class DocCounter(Base):
    """Счётчик номеров документов по префиксу и году."""
    __tablename__ = "doc_counter"
    prefix: Mapped[str] = mapped_column(String(5), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)


def next_number(db: Session, prefix: str, on: date | None = None) -> str:
    year = (on or date.today()).year
    # UPDATE блокирует строку счётчика до конца транзакции – номера не повторяются.
    new = db.execute(
        update(DocCounter)
        .where(DocCounter.prefix == prefix, DocCounter.year == year)
        .values(last_value=DocCounter.last_value + 1)
        .returning(DocCounter.last_value)
    ).scalar()
    if new is None:
        db.add(DocCounter(prefix=prefix, year=year, last_value=1))
        db.flush()
        new = 1
    return f"{prefix}-{year}-{new:06d}"
