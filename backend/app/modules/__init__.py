"""Модули ИС – по функциональным подсистемам ПР 5.

Каждый модуль: models.py (таблицы), schemas.py (схемы API), service.py (бизнес-логика), router.py (HTTP).
Зависимости направлены в одну сторону:
  core ← auth, references ← patients, schedule ← appointments, notifications
       ← procedures, lab ← visits ← cabinet, reports
"""
from importlib import import_module

MODULES = ("auth", "references", "patients", "schedule", "appointments", "notifications",
           "procedures", "lab", "visits", "cabinet", "reports")


def load_models() -> None:
    """Регистрирует таблицы всех модулей в Base.metadata."""
    for name in MODULES:
        try:
            import_module(f"app.modules.{name}.models")
        except ModuleNotFoundError as e:
            if e.name != f"app.modules.{name}.models":
                raise


def routers():
    return [import_module(f"app.modules.{name}.router").router for name in MODULES]
