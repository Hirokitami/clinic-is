from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Role(Base):
    __tablename__ = "ref_role"
    role_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    rights: Mapped[str] = mapped_column(Text)


class UserAccount(Base):
    __tablename__ = "user_account"
    login: Mapped[str] = mapped_column(String(50), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role_code: Mapped[str] = mapped_column(ForeignKey("ref_role.role_code"))
    display_name: Mapped[str] = mapped_column(String(200))
    tab_no: Mapped[str | None] = mapped_column(ForeignKey("doctor.tab_no"))  # для роли DOCTOR
    iin: Mapped[str | None] = mapped_column(ForeignKey("patient.iin"))  # для роли PATIENT
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
