FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY src ./src

# Berkas panduan akademik disimpan di volume /data/panduan
RUN useradd --no-create-home --shell /usr/sbin/nologin identity \
 && mkdir -p /data/panduan && chown -R identity /data
USER identity
ENV PANDUAN_DIR=/data/panduan

EXPOSE 8002
# Migrasi dijalankan sebelum layanan menerima trafik.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --no-access-log"]
