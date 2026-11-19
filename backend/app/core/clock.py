"""Текущие дата и время клиники (одно место – удобно подменять в тестах)."""
from datetime import date, datetime


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def today() -> date:
    return now().date()
