"""Brainstorm judul tugas akhir: ngobrol dulu, kumpulkan kandidat, bahas satu per satu.

Tidak ada yang "terpilih" di sini. Memilih berarti mengajukan lewat `POST /pengajuan-judul` (modul `judul`).
Pesan dan kandidat disimpan pada satu baris per obrolan, hanya dapat dibaca pemiliknya.

Panggilan AI bisa lama, jadi transaksi dilepas dulu; hasilnya ditambahkan pada baris yang dikunci sesudahnya.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.deps import DB, Hal, Pengguna, Saya
from src.api.errors import galat, tidak_ditemukan
from src.api.routes.judul import Masukan, _mata_kuliah_unggul, _prodi_mahasiswa, _teks
from src.domain.tema import TEMA_JUDUL, bakukan
from src.integrations import judul as layanan_judul
from src.integrations.judul import JudulGalat
from src.models import ObrolanJudul, Prodi, RekomendasiJudul

router = APIRouter(tags=["judul"])
log = logging.getLogger("identity.judul")

MAKS_KANDIDAT = 15
MAKS_KONTEKS = 16  # pesan terakhir yang dikirim ke AI


class BuatIn(Masukan):
    pesan: _teks(1000, 3) | None = None
    # Membuka riwayat rekomendasi lama sebagai obrolan, tanpa memanggil AI.
    dari_rekomendasi: uuid.UUID | None = None

    @model_validator(mode="after")
    def _salah_satu(self):
        if (self.pesan is None) == (self.dari_rekomendasi is None):
            raise ValueError("Isi salah satu: pesan atau dari_rekomendasi.")
        return self


class PesanIn(Masukan):
    isi: _teks(1000)
    kandidat_id: _teks(40) | None = None


class SimpanIn(Masukan):
    disimpan: bool


class VersiIn(Masukan):
    pesan_id: _teks(40)


# ------------------------------------------------------------------ pembantu
def _sekarang() -> str:
    return datetime.now(UTC).isoformat()


def _pesan(peran: str, isi: str, kandidat_id: str | None = None, saran: list | None = None, usulan: dict | None = None) -> dict:
    return {
        "id": uuid.uuid4().hex, "peran": peran, "isi": isi, "kandidat_id": kandidat_id,
        "saran": saran or [], "usulan": usulan, "versi_id": None, "dibuat": _sekarang(),
    }


def _kandidat(isi: dict, disimpan: bool = False, versi_dari: str | None = None) -> dict:
    return {
        "id": uuid.uuid4().hex,
        "judul": str(isi.get("judul") or "").strip()[:300],
        "tema": bakukan(isi.get("tema")),
        "deskripsi": str(isi.get("deskripsi") or "")[:2000],
        "metodologi": str(isi.get("metodologi") or "")[:3000],
        "keywords": [str(k)[:60] for k in isi.get("keywords") or []][:10],
        "referensi": list(isi.get("referensi") or [])[:10],
        "disimpan": disimpan, "versi_dari": versi_dari, "dibuat": _sekarang(),
    }


def _keluaran(o: ObrolanJudul) -> dict:
    return {
        "id": str(o.id), "topik": o.topik, "dibuat": o.dibuat.isoformat(), "diubah": o.diubah.isoformat(),
        "pesan": o.pesan, "kandidat": o.kandidat,
    }


def _muat(db: Session, saya: Pengguna, oid: uuid.UUID, kunci: bool = False) -> ObrolanJudul:
    q = select(ObrolanJudul).where(ObrolanJudul.id == oid, ObrolanJudul.mahasiswa_id == saya.orang_id)
    if kunci:
        q = q.with_for_update().execution_options(populate_existing=True)
    o = db.scalar(q)
    if o is None:
        raise tidak_ditemukan("Obrolan")
    return o


def _cari(daftar: list[dict], kunci: str, nama: str) -> dict:
    hasil = next((x for x in daftar if x["id"] == kunci), None)
    if hasil is None:
        raise tidak_ditemukan(nama)
    return hasil


def _konteks_mahasiswa(db: Session, saya: Pengguna) -> tuple[str, list[str]]:
    prodi = db.get(Prodi, _prodi_mahasiswa(saya))
    return prodi.nama if prodi else "", _mata_kuliah_unggul(db, saya.orang_id)


def _tanya_ai(pesan: list[dict], prodi: str, unggul: list[str], kandidat: dict | None = None) -> dict:
    try:
        return layanan_judul.dapatkan_judul().balas(
            [{"peran": p["peran"], "isi": p["isi"][:2000]} for p in pesan[-MAKS_KONTEKS:]],
            prodi, unggul, list(TEMA_JUDUL), kandidat,
        )
    except JudulGalat as exc:
        log.error("Obrolan judul gagal: %s", exc)
        raise galat(502, "AI belum dapat membalas. Coba kirim lagi beberapa saat lagi.") from None


def _balasan(hasil: dict, kandidat_id: str | None = None) -> dict:
    usulan = hasil.get("usulan") if kandidat_id else None
    if usulan:
        usulan = {**usulan, "tema": bakukan(usulan.get("tema"))}
    return _pesan("asisten", str(hasil["balasan"])[:2000], kandidat_id, list(hasil.get("saran") or [])[:4], usulan)


def _pangkas(kandidat: list[dict], pesan: list[dict]) -> list[dict]:
    """Bila terlalu banyak, buang kandidat tertua yang tidak disimpan dan belum pernah dibahas."""
    dibahas = {p["kandidat_id"] for p in pesan if p["kandidat_id"]}
    lebih = len(kandidat) - MAKS_KANDIDAT
    hasil = []
    for k in kandidat:
        if lebih > 0 and not k["disimpan"] and k["id"] not in dibahas:
            lebih -= 1
            continue
        hasil.append(k)
    return hasil


# ------------------------------------------------------------------ rute
@router.get("/judul/obrolan")
def daftar(saya: Saya, db: DB, hal: Hal) -> dict:
    _prodi_mahasiswa(saya)
    kondisi = ObrolanJudul.mahasiswa_id == saya.orang_id
    total = db.scalar(select(func.count()).select_from(ObrolanJudul).where(kondisi)) or 0
    rows = db.scalars(
        select(ObrolanJudul).where(kondisi)
        .order_by(ObrolanJudul.diubah.desc()).offset(hal.offset).limit(hal.ukuran)
    ).all()
    return {"data": [
        {
            "id": str(o.id), "topik": o.topik, "diubah": o.diubah.isoformat(),
            "jumlah_kandidat": len(o.kandidat), "jumlah_disimpan": sum(k["disimpan"] for k in o.kandidat),
        }
        for o in rows
    ], "total": total, "halaman": hal.halaman, "ukuran": hal.ukuran}


@router.post("/judul/obrolan", status_code=201)
def buat(body: BuatIn, saya: Saya, db: DB) -> dict:
    prodi, unggul = _konteks_mahasiswa(db, saya)
    if body.dari_rekomendasi:
        r = db.scalar(select(RekomendasiJudul).where(
            RekomendasiJudul.id == body.dari_rekomendasi, RekomendasiJudul.mahasiswa_id == saya.orang_id))
        if r is None:
            raise tidak_ditemukan("Riwayat rekomendasi")
        o = ObrolanJudul(
            mahasiswa_id=saya.orang_id, topik=r.topik, kandidat=[_kandidat(x) for x in r.hasil],
            pesan=[_pesan("asisten", "Ini kandidat dari rekomendasi sebelumnya. Pilih Bahas pada salah satu, "
                                     "atau lanjutkan cerita minat Anda di sini.")],
        )
    else:
        mahasiswa_id = saya.orang_id
        db.rollback()
        pertama = _pesan("mahasiswa", body.pesan)
        hasil = _tanya_ai([pertama], prodi, unggul)
        o = ObrolanJudul(
            mahasiswa_id=mahasiswa_id, topik=body.pesan[:300], kandidat=[], pesan=[pertama, _balasan(hasil)])
    db.add(o)
    db.commit()
    return _keluaran(o)


@router.get("/judul/obrolan/{oid}")
def ambil(oid: uuid.UUID, saya: Saya, db: DB) -> dict:
    return _keluaran(_muat(db, saya, oid))


@router.post("/judul/obrolan/{oid}/pesan")
def kirim(oid: uuid.UUID, body: PesanIn, saya: Saya, db: DB) -> dict:
    """Satu giliran. Tanpa kandidat_id: brainstorm. Dengan kandidat_id: membahas kandidat itu saja."""
    prodi, unggul = _konteks_mahasiswa(db, saya)
    o = _muat(db, saya, oid)
    kandidat = _cari(o.kandidat, body.kandidat_id, "Kandidat") if body.kandidat_id else None
    baru = _pesan("mahasiswa", body.isi, body.kandidat_id)
    utas = [p for p in o.pesan if p["kandidat_id"] == body.kandidat_id] + [baru]
    if kandidat:
        # Latar minat dari brainstorm ikut dikirim agar pembahasan tidak mulai dari nol.
        latar = " | ".join(p["isi"] for p in o.pesan if p["peran"] == "mahasiswa" and not p["kandidat_id"])
        utas = [{"peran": "mahasiswa", "isi": f"Latar minat saya: {latar or o.topik}"[:2000]}] + utas[-(MAKS_KONTEKS - 1):]
    db.rollback()
    hasil = _tanya_ai(utas, prodi, unggul, kandidat)
    o = _muat(db, saya, oid, kunci=True)
    o.pesan = o.pesan + [baru, _balasan(hasil, body.kandidat_id)]
    o.diubah = datetime.now(UTC)
    db.commit()
    return _keluaran(o)


@router.post("/judul/obrolan/{oid}/kandidat")
def buat_kandidat(oid: uuid.UUID, saya: Saya, db: DB) -> dict:
    """Susun tiga kandidat judul dari arah yang sudah dibicarakan."""
    prodi, unggul = _konteks_mahasiswa(db, saya)
    o = _muat(db, saya, oid)
    topik = o.topik
    baris = [
        f"{'Mahasiswa' if p['peran'] == 'mahasiswa' else 'Pembimbing'}: {p['isi']}"
        for p in o.pesan if not p["kandidat_id"]
    ]
    diskusi = "\n".join(baris)[-2300:]
    if o.kandidat:
        diskusi += "\nSudah pernah diusulkan, jangan diulang: " + "; ".join(k["judul"][:100] for k in o.kandidat[-5:])
    db.rollback()
    try:
        hasil = layanan_judul.dapatkan_judul().rekomendasi(topik, prodi, unggul, list(TEMA_JUDUL), diskusi[:3000])
    except JudulGalat as exc:
        log.error("Kandidat judul gagal: %s", exc)
        raise galat(502, "Kandidat belum dapat disusun. Coba lagi beberapa saat lagi.") from None
    baru = [_kandidat(x) for x in hasil if isinstance(x, dict) and str(x.get("judul") or "").strip()]
    if not baru:
        raise galat(502, "Kandidat belum dapat disusun. Coba lagi beberapa saat lagi.")
    o = _muat(db, saya, oid, kunci=True)
    catatan = _pesan("asisten", f"Saya tambahkan {len(baru)} kandidat judul. Belum ada yang dipilih: "
                                "bahas yang menarik, simpan yang ingin dibandingkan.")
    o.pesan = o.pesan + [catatan]
    o.kandidat = _pangkas(o.kandidat + baru, o.pesan)
    o.diubah = datetime.now(UTC)
    db.commit()
    return _keluaran(o)


@router.patch("/judul/obrolan/{oid}/kandidat/{kid}")
def simpan_kandidat(oid: uuid.UUID, kid: str, body: SimpanIn, saya: Saya, db: DB) -> dict:
    _prodi_mahasiswa(saya)
    o = _muat(db, saya, oid, kunci=True)
    _cari(o.kandidat, kid, "Kandidat")
    o.kandidat = [{**k, "disimpan": body.disimpan} if k["id"] == kid else k for k in o.kandidat]
    o.diubah = datetime.now(UTC)
    db.commit()
    return _keluaran(o)


@router.post("/judul/obrolan/{oid}/versi")
def simpan_versi(oid: uuid.UUID, body: VersiIn, saya: Saya, db: DB) -> dict:
    """Simpan usulan perbaikan dari pembahasan sebagai kandidat baru; yang lama tetap ada."""
    _prodi_mahasiswa(saya)
    o = _muat(db, saya, oid, kunci=True)
    p = _cari(o.pesan, body.pesan_id, "Usulan")
    if not p.get("usulan"):
        raise tidak_ditemukan("Usulan")
    if p.get("versi_id"):
        raise galat(409, "Usulan ini sudah disimpan.")
    asal = next((k for k in o.kandidat if k["id"] == p["kandidat_id"]), None)
    versi = _kandidat(
        {**p["usulan"], "referensi": (asal or {}).get("referensi", [])}, disimpan=True, versi_dari=p["kandidat_id"])
    o.kandidat = o.kandidat + [versi]
    o.pesan = [{**x, "versi_id": versi["id"]} if x["id"] == p["id"] else x for x in o.pesan]
    o.kandidat = _pangkas(o.kandidat, o.pesan)
    o.diubah = datetime.now(UTC)
    db.commit()
    return _keluaran(o)
