from __future__ import annotations

from fastapi import FastAPI

from src.api.errors import pasang_penangan
from src.api.routes import akademik, audit, auth, internal, orang, panduan, pengajuan, penugasan, ringkasan, struktur

app = FastAPI(title="identity", version="0.1.0")
pasang_penangan(app)


@app.get("/health", tags=["sistem"])
def health() -> dict:
    return {"status": "ok"}


for modul in (auth, struktur, orang, penugasan, pengajuan, panduan, akademik, audit, ringkasan, internal):
    app.include_router(modul.router)
