from datetime import date

from sqlalchemy import CheckConstraint, Date, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Patient(Base):
    """Электронная карта пациента. Идентификатор – ИИН (Т1, Т3)."""
    __tablename__ = "patient"
    iin: Mapped[str] = mapped_column(String(12), primary_key=True)
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100))
    birth_date: Mapped[date] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(1))
    mobile_phone: Mapped[str] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(300))
    doc_type: Mapped[str | None] = mapped_column(String(100))
    doc_no: Mapped[str | None] = mapped_column(String(50))
    reg_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    __table_args__ = (
        CheckConstraint("length(iin) = 12"),
        CheckConstraint("sex IN ('М', 'Ж')"),
        Index("ix_patient_name_birth", "last_name", "birth_date"),
    )

    @property
    def fio(self) -> str:
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)
