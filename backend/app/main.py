"""Точка входа API.  Запуск:  uvicorn app.main:app --reload   (документация: /docs)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.db import Base, engine
from .modules import load_models, routers

load_models()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)  # создаёт недостающие таблицы; демо-данные – python -m app.seed
    yield


app = FastAPI(lifespan=lifespan, title="ИС медицинской клиники", version="2.0.0",
              description="Регистратура, расписание врачей, приём пациента, процедуры, лаборатория, "
                          "личный кабинет пациента, администрирование.")

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
async def validation_handler(_req, exc: RequestValidationError):
    fields = {}
    for err in exc.errors():
        loc = [str(x) for x in err["loc"] if x not in ("body", "query", "path")]
        fields[".".join(loc) or "request"] = err["msg"]
    return JSONResponse(status_code=422, content={"detail": {"code": "VALIDATION",
                                                             "message": "Проверьте заполнение полей",
                                                             "fields": fields}})


for r in routers():
    app.include_router(r)


@app.get("/api/health", tags=["Служебное"])
def health():
    return {"status": "ok"}
