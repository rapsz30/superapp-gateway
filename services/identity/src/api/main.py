from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.errors import pasang_penangan
from src.api.routes import akademik, analitik, audit, auth, internal, judul, obrolan_judul, orang, panduan, pengajuan, penugasan, ringkasan, struktur
from src.domain import akun_alurkerja


@asynccontextmanager
async def _hidup(_: FastAPI):
    berhenti = akun_alurkerja.mulai_latar()  # None bila sinkron akun tidak dikonfigurasi
    yield
    if berhenti:
        berhenti.set()


app = FastAPI(title="identity", version="0.1.0", lifespan=_hidup)
pasang_penangan(app)


@app.get("/health", tags=["sistem"])
def health() -> dict:
    return {"status": "ok"}


for modul in (auth, struktur, orang, penugasan, pengajuan, panduan, akademik, audit, ringkasan, analitik, judul, obrolan_judul, internal):
    app.include_router(modul.router)
