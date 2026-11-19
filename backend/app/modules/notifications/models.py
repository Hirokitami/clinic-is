from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SmsOutbox(Base):
    """Исходящие SMS-подтверждения (Т8)."""
    __tablename__ = "sms_outbox"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appt_no: Mapped[str] = mapped_column(ForeignKey("appointment.appt_no"))
    phone: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), default="имитация отправки")
