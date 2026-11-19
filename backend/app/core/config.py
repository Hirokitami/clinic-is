from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # каталог backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLINIC_", env_file=BASE_DIR / ".env", extra="ignore")

    # SQLite по умолчанию; для PostgreSQL: postgresql+psycopg://user:pass@host/db
    database_url: str = f"sqlite:///{(BASE_DIR / 'clinic.db').as_posix()}"
    secret_key: str = "dev-only-secret-change-me-in-production-0123456789"
    token_minutes: int = 12 * 60
    cookie_name: str = "clinic_token"
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # Шлюз SMS: "mock" – сообщение сохраняется в журнале sms_outbox без отправки (Т8).
    sms_gateway: str = "mock"
    clinic_name: str = "Клиника"


settings = Settings()
