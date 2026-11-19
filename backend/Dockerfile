FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Almaty

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY tests ./tests

RUN useradd --create-home clinic && chown -R clinic /app
USER clinic

EXPOSE 8000
# Демо-данные загружаются только в пустую БД; перезапуск контейнера данные не стирает.
CMD ["sh", "-c", "python -m app.seed --if-empty && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
