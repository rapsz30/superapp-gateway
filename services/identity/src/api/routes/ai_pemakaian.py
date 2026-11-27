"""Pemakaian AI: layanan mencatat lewat endpoint internal, superadmin membaca ringkasannya."""

from __future__ import annotations

import hmac
import uuid
from datetime import date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, Response
from pydantic import BaseModel, Field
from sqlalchemy import Date, case, cast, func, literal_column, select

from src.api.deps import DB, Hari, Superadmin
from src.api.errors import galat, tidak_ditemukan
from src.core.config import get_settings
from src.models import AiPemakaian, Akun, Orang, Pengajuan

router = APIRouter(tags=["pemakaian-ai"])

MAKS_HARI = 366
MAKS_PENGGUNA = 20
MAKS_TOKEN = 100_000_000


class CatatanIn(BaseModel):
    layanan: Literal["matkul", "judul", "microcred"]
    fitur: str = Field(pattern=r"^[a-z_]{1,40}$")
    model: str = Field(min_length=1, max_length=60)
    token_masuk: int = Field(0, ge=0, le=MAKS_TOKEN)
    token_keluar: int = Field(0, ge=0, le=MAKS_TOKEN)
    durasi_ms: int = Field(0, ge=0, le=3_600_000)
    berhasil: bool = True
    akun_id: uuid.UUID | None = None
    # Dipakai langkah yang dijalankan proses (tanpa pengguna login): pemakaian dicatat atas mahasiswanya.
    pengajuan_id: uuid.UUID | None = None


@router.post("/internal/ai-pemakaian", status_code=204, include_in_schema=False)
def catat(body: CatatanIn, db: DB, x_ai_token: str = Header("")) -> Response:
    rahasia = get_settings().ai_catat_token
    if not rahasia or not hmac.compare_digest(x_ai_token.encode(), rahasia.encode()):
        raise tidak_ditemukan("Halaman")
    akun_id = body.akun_id
    if akun_id is None and body.pengajuan_id is not None:
        akun_id = db.scalar(
            select(Akun.id)
            .join(Pengajuan, Pengajuan.mahasiswa_id == Akun.orang_id)
            .where(Pengajuan.id == body.pengajuan_id)
        )
    db.add(AiPemakaian(**body.model_dump(exclude={"akun_id", "pengajuan_id"}), akun_id=akun_id))
    db.commit()
    return Response(status_code=204)


def _harga() -> dict | None:
    s = get_settings()
    try:
        masuk, keluar = float(s.ai_harga_masuk_per_juta), float(s.ai_harga_keluar_per_juta)
    except ValueError:
        return None
    return {"masuk_per_juta": masuk, "keluar_per_juta": keluar}


def _jumlah() -> list:
    return [
        func.count().label("panggilan"),
        func.coalesce(func.sum(case((AiPemakaian.berhasil, 0), else_=1)), 0).label("gagal"),
        func.coalesce(func.sum(AiPemakaian.token_masuk), 0).label("token_masuk"),
        func.coalesce(func.sum(AiPemakaian.token_keluar), 0).label("token_keluar"),
    ]


def _angka(baris) -> dict:
    return {k: int(getattr(baris, k)) for k in ("panggilan", "gagal", "token_masuk", "token_keluar")}


@router.get("/ai-pemakaian")
def ringkasan(_: Superadmin, db: DB, hari: Hari, dari: date | None = None, sampai: date | None = None) -> dict:
    """Rentang tanggal inklusif menurut zona waktu kampus; bawaan 30 hari terakhir."""
    sampai = sampai or hari
    dari = dari or sampai - timedelta(days=29)
    if dari > sampai or (sampai - dari).days >= MAKS_HARI:
        raise galat(400, f"Rentang tanggal tidak sah (maksimal {MAKS_HARI} hari).")
    zona = get_settings().zona_waktu
    tz = ZoneInfo(zona)
    dalam = (
        AiPemakaian.waktu >= datetime.combine(dari, time.min, tz),
        AiPemakaian.waktu < datetime.combine(sampai + timedelta(days=1), time.min, tz),
    )

    total = _angka(db.execute(select(*_jumlah()).where(*dalam)).one())
    harga = _harga()
    total["biaya_usd"] = None
    if harga is not None:
        biaya = (
            total["token_masuk"] * harga["masuk_per_juta"] + total["token_keluar"] * harga["keluar_per_juta"]
        ) / 1_000_000
        total["biaya_usd"] = round(biaya, 4)

    # Zona ditulis sebagai literal supaya ekspresi di SELECT dan GROUP BY dikenali sama oleh Postgres.
    tanggal = cast(func.timezone(literal_column(f"'{zona}'"), AiPemakaian.waktu), Date).label("tanggal")
    harian = {
        r.tanggal: _angka(r)
        for r in db.execute(select(tanggal, *_jumlah()).where(*dalam).group_by(tanggal)).all()
    }
    kosong = {"panggilan": 0, "gagal": 0, "token_masuk": 0, "token_keluar": 0}
    per_hari = []
    for i in range((sampai - dari).days + 1):
        t = dari + timedelta(days=i)
        per_hari.append({"tanggal": t.isoformat(), **harian.get(t, kosong)})

    kunci = (AiPemakaian.layanan, AiPemakaian.fitur, AiPemakaian.model)
    per_fitur = [
        {
            "layanan": r.layanan,
            "fitur": r.fitur,
            "model": r.model,
            "rata_durasi_ms": int(r.durasi or 0),
            **_angka(r),
        }
        for r in db.execute(
            select(*kunci, func.avg(AiPemakaian.durasi_ms).label("durasi"), *_jumlah())
            .where(*dalam)
            .group_by(*kunci)
            .order_by(func.count().desc())
        ).all()
    ]

    token = func.sum(AiPemakaian.token_masuk + AiPemakaian.token_keluar)
    baris = db.execute(
        select(AiPemakaian.akun_id, *_jumlah())
        .where(*dalam)
        .group_by(AiPemakaian.akun_id)
        .order_by(token.desc(), func.count().desc())
        .limit(MAKS_PENGGUNA)
    ).all()
    ids = [r.akun_id for r in baris if r.akun_id]
    nama = {
        a: (n, e)
        for a, n, e in db.execute(
            select(Akun.id, Orang.nama_lengkap, Akun.email)
            .join(Orang, Orang.id == Akun.orang_id)
            .where(Akun.id.in_(ids))
        ).all()
    }
    per_pengguna = [
        {
            "akun_id": str(r.akun_id) if r.akun_id else None,
            "nama": nama.get(r.akun_id, (None, None))[0],
            "email": nama.get(r.akun_id, (None, None))[1],
            **_angka(r),
        }
        for r in baris
    ]
    return {
        "dari": dari.isoformat(),
        "sampai": sampai.isoformat(),
        "harga": harga,
        "total": total,
        "per_hari": per_hari,
        "per_fitur": per_fitur,
        "per_pengguna": per_pengguna,
    }
