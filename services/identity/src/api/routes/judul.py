"""Judul tugas akhir: rekomendasi, pilihan pembimbing TA per pengajuan, dan pengajuan judul lewat AlurKerja.

Alur (BPMN `pengajuan-judul-superapp`): mahasiswa mengajukan -> pembimbing TA meninjau di Tasklist atau di web ->
setuju (selesai), atau revisi -> mahasiswa memperbaiki di web -> ditinjau lagi.

Mode `alurkerja` bila AlurKerja dikonfigurasi (keadaan dibaca dari AlurKerja saat dibuka); `lokal` tanpa itu.
"""

from __future__ import annotations

import html
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.api.deps import DB, Hal, Hari, Pengguna, Saya
from src.api.errors import dilarang, galat, tidak_ditemukan
from src.core.config import get_settings
from src.domain import audit
from src.domain.cakupan import penugasan_aktif, prodi_dicakup_pa
from src.domain.tema import TEMA_JUDUL, bakukan
from src.integrations import alurkerja, judul as layanan_judul, matkul
from src.integrations.alurkerja import AlurKerjaGalat, Snapshot
from src.integrations.judul import JudulGalat
from src.integrations.matkul import MatkulGalat
from src.models import (
    Akun,
    KeanggotaanProdi,
    Orang,
    PembimbingTA,
    Pengajuan,
    PengajuanJudul,
    Penugasan,
    Prodi,
    RekomendasiJudul,
)

router = APIRouter(tags=["judul"])
log = logging.getLogger("identity.judul")

TUGAS_TINJAU = "Task_TinjauJudul"
TUGAS_PERBAIKI = "Task_PerbaikiJudul"
TAHAP_DARI_AKTIVITAS = {TUGAS_TINJAU: "tinjau", TUGAS_PERBAIKI: "perbaikan"}
MAKS_RINGKASAN = 3900  # Camunda menyimpan variabel String paling panjang 4000 karakter
MAKS_RIWAYAT = 10
NILAI_UNGGUL = {"A", "A-", "A/B"}


# ------------------------------------------------------------------ masukan
def _teks(maks: int, minimal: int = 1):
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=minimal, max_length=maks)]


class Masukan(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MinatIn(Masukan):
    minat: _teks(300, 3)


class ReferensiIn(Masukan):
    sitasi: _teks(600)
    link: Annotated[str, StringConstraints(strip_whitespace=True, max_length=600, pattern=r"^https?://\S+$")]


class JudulIn(Masukan):
    topik: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ""
    pembimbing_id: uuid.UUID | None = None
    judul: _teks(300, 10)
    tema: _teks(80)
    deskripsi: _teks(2000, 20)
    metodologi: Annotated[str, StringConstraints(strip_whitespace=True, max_length=3000)] = ""
    keywords: list[_teks(60)] = Field(default_factory=list, max_length=10)
    referensi: list[ReferensiIn] = Field(default_factory=list, max_length=10)

    @field_validator("tema")
    @classmethod
    def _tema_baku(cls, v: str) -> str:
        if v not in TEMA_JUDUL:
            raise ValueError("Tema harus salah satu dari daftar tema (GET /judul/tema).")
        return v


class KeputusanJudulIn(Masukan):
    keputusan: Literal["setuju", "revisi"]
    catatan: str | None = Field(default=None, max_length=1000)


class PembimbingIn(Masukan):
    mahasiswa_id: uuid.UUID
    dosen_id: uuid.UUID


# ------------------------------------------------------------------ pembantu
def _klien():
    return alurkerja.dapatkan_klien(get_settings().alurkerja_process_key_judul)


def _email(db: Session, orang_id: uuid.UUID) -> str | None:
    akun = db.scalar(select(Akun).where(Akun.orang_id == orang_id))
    return akun.email.strip().lower() if akun else None


def _orang(db: Session, orang_id: uuid.UUID) -> dict | None:
    o = db.get(Orang, orang_id)
    return {"id": str(o.id), "nama_lengkap": o.nama_lengkap, "nim": o.nim} if o else None


def _pembimbing_aktif(db: Session, mahasiswa_id: uuid.UUID) -> PembimbingTA | None:
    return db.scalar(
        select(PembimbingTA).where(PembimbingTA.mahasiswa_id == mahasiswa_id, PembimbingTA.selesai.is_(None))
    )


def ringkasan_judul(p: PengajuanJudul, prodi: str) -> str:
    """HTML yang dibaca dosen di atas keputusan pada form Tasklist (tanpa nama dan NIM)."""
    aman = html.escape
    baris = "".join(f"<li>{aman(x.strip(' -'))}</li>" for x in p.metodologi.splitlines() if x.strip(" -"))
    sumber = "".join(f"<li>{aman(r['sitasi'])} ({aman(r['link'])})</li>" for r in p.referensi)
    bagian = [
        f"<p><strong>{aman(p.judul)}</strong></p>",
        f"<p>Tema: <strong>{aman(p.tema)}</strong> · Prodi {aman(prodi)}" + (f" · Minat: {aman(p.topik)}" if p.topik else "") + "</p>",
        f"<p><strong>Revisi ke-{p.jumlah_revisi}</strong> atas catatan: {aman(p.catatan or '-')}</p>" if p.jumlah_revisi else "",
        f"<p>{aman(p.deskripsi)}</p>",
        f"<p><strong>Metodologi</strong></p><ul>{baris}</ul>" if baris else "",
        f"<p>Kata kunci: {aman(', '.join(p.keywords))}</p>" if p.keywords else "",
        f"<p><strong>Referensi</strong></p><ul>{sumber}</ul>" if sumber else "",
    ]
    hasil = ""
    for b in bagian:  # yang tidak muat dibuang utuh agar tag HTML tidak terpotong
        if len(hasil) + len(b) > MAKS_RINGKASAN - 100:
            return hasil + "<p>Rangkuman dipotong. Buka aplikasi untuk isi lengkap.</p>"
        hasil += b
    return hasil


def _keluaran(db: Session, p: PengajuanJudul) -> dict:
    prodi = db.get(Prodi, p.prodi_id)
    return {
        "id": str(p.id),
        "status": p.status,
        "tahap": p.tahap,
        "mode": p.mode,
        "topik": p.topik,
        "judul": p.judul,
        "tema": p.tema,
        "deskripsi": p.deskripsi,
        "metodologi": p.metodologi,
        "keywords": p.keywords,
        "referensi": p.referensi,
        "catatan": p.catatan,
        "jumlah_revisi": p.jumlah_revisi,
        "mahasiswa": _orang(db, p.mahasiswa_id),
        "pembimbing": _orang(db, p.pembimbing_id),
        "prodi": {"id": str(prodi.id), "kode": prodi.kode, "nama": prodi.nama} if prodi else None,
        "diajukan_pada": p.diajukan_pada.isoformat(),
        "diputuskan_pada": p.diputuskan_pada.isoformat() if p.diputuskan_pada else None,
    }


def _terapkan_snapshot(p: PengajuanJudul, snap: Snapshot) -> bool:
    sebelum = (p.status, p.tahap, p.catatan)
    keputusan = snap.variabel.get("keputusan")
    catatan = snap.variabel.get("catatan_dosen")
    if keputusan == "revisi" and catatan:
        p.catatan = str(catatan)
    if snap.selesai:
        if snap.state == "COMPLETED" and keputusan == "setuju":
            p.status, p.tahap = "disetujui", "selesai"
            if catatan:
                p.catatan = str(catatan)
        else:
            p.status = "dibatalkan"
            p.catatan = p.catatan or f"Proses di AlurKerja berakhir ({snap.state})."
        p.diputuskan_pada = p.diputuskan_pada or datetime.now(UTC)
    else:
        for aktivitas in snap.aktif:
            if aktivitas in TAHAP_DARI_AKTIVITAS:
                p.tahap = TAHAP_DARI_AKTIVITAS[aktivitas]
                break
    return sebelum != (p.status, p.tahap, p.catatan)


def _sinkron(db: Session, p: PengajuanJudul) -> bool:
    """Baca keadaan proses dari AlurKerja. Galat jaringan tidak mengubah apa pun."""
    if p.status != "diajukan" or p.mode != "alurkerja" or not p.alurkerja_instance_id:
        return False
    klien = _klien()
    if klien is None:
        return False
    try:
        snap = klien.snapshot(p.alurkerja_instance_id)
    except AlurKerjaGalat as exc:
        log.warning("Sinkron AlurKerja gagal untuk judul %s: %s", p.id, exc)
        return False
    lama = p.status
    berubah = _terapkan_snapshot(p, snap)
    if berubah and p.status != lama:
        audit.catat(db, None, f"judul.{p.status}", "pengajuan_judul", p.id, {"status": lama}, {"status": p.status})
    return berubah


def _selesaikan(p: PengajuanJudul, tugas: str, variabel: dict[str, Any]) -> None:
    """Selesaikan tugas manusia di AlurKerja; 502 bila AlurKerja gagal, 409 bila tugas sudah tidak terbuka."""
    if p.mode != "alurkerja":
        return
    klien = _klien()
    try:
        if klien is None or not p.alurkerja_instance_id:
            raise AlurKerjaGalat("AlurKerja tidak dikonfigurasi.")
        ada = klien.selesaikan_tugas(p.alurkerja_instance_id, tugas, variabel)
    except AlurKerjaGalat as exc:
        log.error("Gagal menyelesaikan %s untuk judul %s: %s", tugas, p.id, exc)
        raise galat(502, "Belum dapat diteruskan ke AlurKerja. Coba lagi beberapa saat lagi.") from None
    if not ada:
        raise galat(409, "Tugas ini sudah tidak terbuka di AlurKerja. Muat ulang halaman.")


def _terlihat(saya: Pengguna):
    cak = saya.cakupan
    if cak.superadmin:
        return None
    kondisi = [PengajuanJudul.mahasiswa_id == saya.orang_id, PengajuanJudul.pembimbing_id == saya.orang_id]
    if cak.prodi_ids:
        kondisi.append(PengajuanJudul.prodi_id.in_(cak.prodi_ids))
    return or_(*kondisi)


def _muat(db: Session, saya: Pengguna, pid: uuid.UUID) -> PengajuanJudul:
    q = select(PengajuanJudul).where(PengajuanJudul.id == pid)
    kondisi = _terlihat(saya)
    if kondisi is not None:
        q = q.where(kondisi)
    p = db.scalar(q)
    if p is None:
        raise tidak_ditemukan("Pengajuan judul")
    return p


def _prodi_mahasiswa(saya: Pengguna) -> uuid.UUID:
    if saya.cakupan.prodi_mahasiswa is None:
        raise dilarang("Fitur ini untuk mahasiswa.")
    return saya.cakupan.prodi_mahasiswa


# ------------------------------------------------------------------ rekomendasi
def _mata_kuliah_unggul(db: Session, mahasiswa_id: uuid.UUID) -> list[str]:
    """Mata kuliah bernilai tinggi dari KHS terbaru (hanya nama mata kuliah). Kosong bila belum ada."""
    p = db.scalar(
        select(Pengajuan)
        .where(Pengajuan.mahasiswa_id == mahasiswa_id, Pengajuan.status != "dibatalkan")
        .order_by(Pengajuan.diajukan_pada.desc())
        .limit(1)
    )
    d = (p.data_proses or {}) if p else {}
    if not d.get("khs_ref") or d.get("nim_cocok") is False:
        return []
    try:
        ringkas = matkul.dapatkan_matkul().ringkasan_khs(str(d["khs_ref"]))
    except MatkulGalat as exc:
        log.warning("Nilai untuk rekomendasi judul tidak terbaca: %s", exc)
        return []
    return [
        str(mk["nama"])[:80]
        for s in ringkas.get("per_semester") or []
        for mk in s.get("mk") or []
        if mk.get("nilai") in NILAI_UNGGUL and mk.get("nama")
    ][:12]


@router.post("/judul/rekomendasi")
def rekomendasi(body: MinatIn, saya: Saya, db: DB) -> dict:
    """Tiga rekomendasi judul memakai prodi dan nilai tertinggi mahasiswa. Hasilnya disimpan sebagai riwayat."""
    prodi = db.get(Prodi, _prodi_mahasiswa(saya))
    unggul = _mata_kuliah_unggul(db, saya.orang_id)
    try:
        hasil = layanan_judul.dapatkan_judul().rekomendasi(
            body.minat, prodi.nama if prodi else "", unggul, list(TEMA_JUDUL)
        )
    except JudulGalat as exc:
        log.error("Rekomendasi judul gagal: %s", exc)
        raise galat(502, "Rekomendasi belum dapat disusun. Coba lagi beberapa saat lagi.") from None
    hasil = [{**item, "tema": bakukan(item.get("tema"))} for item in hasil if isinstance(item, dict)]
    r = RekomendasiJudul(mahasiswa_id=saya.orang_id, topik=body.minat, hasil=hasil)
    db.add(r)
    db.commit()
    return {"id": str(r.id), "topik": r.topik, "rekomendasi": hasil, "memakai_nilai": bool(unggul)}


@router.get("/judul/saya")
def judul_saya(saya: Saya, db: DB) -> dict:
    """Bahan halaman mahasiswa: pembimbing TA, pengajuan terbaru, dan riwayat rekomendasi."""
    _prodi_mahasiswa(saya)
    pb = _pembimbing_aktif(db, saya.orang_id)
    p = db.scalar(
        select(PengajuanJudul)
        .where(PengajuanJudul.mahasiswa_id == saya.orang_id)
        .order_by(PengajuanJudul.diajukan_pada.desc())
        .limit(1)
    )
    if p is not None and _sinkron(db, p):
        db.commit()
    riwayat = db.scalars(
        select(RekomendasiJudul)
        .where(RekomendasiJudul.mahasiswa_id == saya.orang_id)
        .order_by(RekomendasiJudul.dibuat.desc())
        .limit(MAKS_RIWAYAT)
    ).all()
    return {
        "pembimbing": _orang(db, pb.dosen_id) if pb else None,
        "pengajuan": _keluaran(db, p) if p else None,
        "riwayat": [
            {"id": str(r.id), "topik": r.topik, "dibuat": r.dibuat.isoformat(), "rekomendasi": r.hasil} for r in riwayat
        ],
    }


@router.get("/judul/riwayat")
def daftar_riwayat_judul(saya: Saya, db: DB, hal: Hal) -> dict:
    """Ringkasan arsip rekomendasi mahasiswa dengan pagination."""
    _prodi_mahasiswa(saya)
    kondisi = RekomendasiJudul.mahasiswa_id == saya.orang_id
    total = db.scalar(select(func.count()).select_from(RekomendasiJudul).where(kondisi)) or 0
    rows = db.scalars(
        select(RekomendasiJudul).where(kondisi)
        .order_by(RekomendasiJudul.dibuat.desc()).offset(hal.offset).limit(hal.ukuran)
    ).all()
    return {"data": [
        {"id": str(item.id), "topik": item.topik, "dibuat": item.dibuat.isoformat(), "jumlah_rekomendasi": len(item.hasil)}
        for item in rows
    ], "total": total, "halaman": hal.halaman, "ukuran": hal.ukuran}


@router.get("/judul/pembimbing")
def pilihan_pembimbing(saya: Saya, db: DB, hari: Hari) -> dict:
    """Dosen aktif yang dapat membimbing mahasiswa pada program studinya."""
    prodi_id = _prodi_mahasiswa(saya)
    return {"data": [
        {"id": str(o.id), "nama_lengkap": o.nama_lengkap}
        for o in _dosen_prodi(db, prodi_id, hari) if o.id != saya.orang_id
    ]}


# ------------------------------------------------------------------ tema
@router.get("/judul/tema")
def daftar_tema(saya: Saya) -> dict:
    return {"data": list(TEMA_JUDUL)}


@router.get("/judul/statistik-tema")
def statistik_tema(saya: Saya, db: DB, prodi_id: uuid.UUID | None = None) -> dict:
    """Tema yang paling banyak diambil per program studi (tanpa identitas mahasiswa).

    Dihitung dari pengajuan judul yang disetujui atau masih berjalan; yang dibatalkan tidak dihitung.
    Terbuka untuk kaprodi, kajur, dekan (sebatas cakupannya) dan superadmin.
    """
    cak = saya.cakupan
    if not (cak.superadmin or cak.prodi_ids):
        raise dilarang("Rekap tema hanya untuk pengelola program studi.")
    if prodi_id and not (cak.superadmin or prodi_id in cak.prodi_ids):
        raise dilarang("Program studi ini di luar cakupan Anda.")
    q = (
        select(PengajuanJudul.prodi_id, PengajuanJudul.tema, PengajuanJudul.status, func.count())
        .where(PengajuanJudul.status != "dibatalkan")
        .group_by(PengajuanJudul.prodi_id, PengajuanJudul.tema, PengajuanJudul.status)
    )
    if prodi_id:
        q = q.where(PengajuanJudul.prodi_id == prodi_id)
    elif not cak.superadmin:
        q = q.where(PengajuanJudul.prodi_id.in_(cak.prodi_ids))
    # Pengajuan yang masih berjalan ikut disegarkan dari AlurKerja agar rekap tidak tertinggal.
    terbuka = select(PengajuanJudul).where(PengajuanJudul.status == "diajukan").limit(20)
    if prodi_id:
        terbuka = terbuka.where(PengajuanJudul.prodi_id == prodi_id)
    elif not cak.superadmin:
        terbuka = terbuka.where(PengajuanJudul.prodi_id.in_(cak.prodi_ids))
    berubah = False
    for p in db.scalars(terbuka).all():
        berubah |= _sinkron(db, p)
    if berubah:
        db.commit()

    rekap: dict[uuid.UUID, dict[str, dict[str, int]]] = {}
    for pid, tema, status, jumlah in db.execute(q).all():
        baris = rekap.setdefault(pid, {}).setdefault(tema, {"disetujui": 0, "berjalan": 0})
        baris["disetujui" if status == "disetujui" else "berjalan"] += jumlah
    data = []
    for pid, per_tema in rekap.items():
        prodi = db.get(Prodi, pid)
        daftar = sorted(
            ({"tema": t, **n, "total": n["disetujui"] + n["berjalan"]} for t, n in per_tema.items()),
            key=lambda x: (-x["total"], -x["disetujui"], x["tema"]),
        )
        data.append({
            "prodi": {"id": str(prodi.id), "kode": prodi.kode, "nama": prodi.nama},
            "total": sum(x["total"] for x in daftar),
            "tema": daftar,
        })
    return {"data": sorted(data, key=lambda x: x["prodi"]["nama"])}


# ------------------------------------------------------------------ pembimbing TA
def _boleh_atur(saya: Pengguna, prodi_id: uuid.UUID) -> None:
    if not (saya.superadmin or prodi_id in saya.cakupan.kaprodi_ids):
        raise dilarang("Hanya kaprodi prodi ini yang dapat menunjuk pembimbing tugas akhir.")


def _dosen_prodi(db: Session, prodi_id: uuid.UUID, hari) -> list[Orang]:
    """Dosen yang dapat membimbing: dosen PA yang mencakup prodi ini atau kaprodinya, dan punya akun."""
    calon = db.scalars(
        select(Orang)
        .join(Penugasan, Penugasan.orang_id == Orang.id)
        .join(Akun, Akun.orang_id == Orang.id)
        .where(Penugasan.peran.in_(("dosen_pa", "kaprodi")), penugasan_aktif(hari), Akun.status == "aktif")
        .distinct()
        .order_by(Orang.nama_lengkap)
    ).all()

    def mencakup(o: Orang) -> bool:
        if prodi_id in prodi_dicakup_pa(db, o.id, hari):
            return True
        return db.scalar(
            select(func.count()).select_from(Penugasan).where(
                Penugasan.orang_id == o.id, Penugasan.peran == "kaprodi", Penugasan.unit_id == prodi_id,
                penugasan_aktif(hari),
            )
        ) > 0

    return [o for o in calon if mencakup(o)]


@router.get("/pembimbing-ta/dosen")
def daftar_dosen(prodi_id: uuid.UUID, saya: Saya, db: DB, hari: Hari) -> dict:
    _boleh_atur(saya, prodi_id)
    return {"data": [{"id": str(o.id), "nama_lengkap": o.nama_lengkap} for o in _dosen_prodi(db, prodi_id, hari)]}


@router.get("/pembimbing-ta")
def daftar_pembimbing(prodi_id: uuid.UUID, saya: Saya, db: DB, hal: Hal) -> dict:
    """Mahasiswa aktif prodi beserta pembimbing TA dan status judul terakhirnya."""
    _boleh_atur(saya, prodi_id)
    q = (
        select(Orang)
        .join(KeanggotaanProdi, KeanggotaanProdi.orang_id == Orang.id)
        .where(KeanggotaanProdi.prodi_id == prodi_id, KeanggotaanProdi.selesai.is_(None))
    )
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    data = []
    for o in db.scalars(q.order_by(Orang.nama_lengkap).offset(hal.offset).limit(hal.ukuran)).all():
        pb = _pembimbing_aktif(db, o.id)
        p = db.scalar(
            select(PengajuanJudul).where(PengajuanJudul.mahasiswa_id == o.id)
            .order_by(PengajuanJudul.diajukan_pada.desc()).limit(1)
        )
        data.append({
            "mahasiswa": {"id": str(o.id), "nama_lengkap": o.nama_lengkap, "nim": o.nim},
            "pembimbing": _orang(db, pb.dosen_id) if pb else None,
            "judul": {"status": p.status, "tahap": p.tahap, "judul": p.judul, "tema": p.tema} if p else None,
        })
    return {"data": data, "total": total}


@router.put("/pembimbing-ta")
def tunjuk_pembimbing(body: PembimbingIn, saya: Saya, db: DB, hari: Hari) -> dict:
    """Tunjuk atau ganti pembimbing TA. Pengajuan judul yang berjalan ikut pindah, juga tugasnya di AlurKerja."""
    anggota = db.scalar(
        select(KeanggotaanProdi).where(
            KeanggotaanProdi.orang_id == body.mahasiswa_id, KeanggotaanProdi.selesai.is_(None)
        )
    )
    if anggota is None:
        raise galat(400, "Mahasiswa tidak terdaftar aktif di program studi mana pun.")
    _boleh_atur(saya, anggota.prodi_id)
    if body.dosen_id == body.mahasiswa_id or body.dosen_id not in {o.id for o in _dosen_prodi(db, anggota.prodi_id, hari)}:
        raise galat(400, "Dosen tersebut tidak dapat membimbing di program studi ini (perlu penugasan dan akun aktif).")
    lama = _pembimbing_aktif(db, body.mahasiswa_id)
    if lama is not None and lama.dosen_id == body.dosen_id:
        return {"pembimbing": _orang(db, body.dosen_id)}
    if lama is not None:
        lama.selesai = hari
        db.flush()
    baru = PembimbingTA(mahasiswa_id=body.mahasiswa_id, dosen_id=body.dosen_id, mulai=hari)
    db.add(baru)
    db.flush()

    p = db.scalar(
        select(PengajuanJudul).where(
            PengajuanJudul.mahasiswa_id == body.mahasiswa_id, PengajuanJudul.status == "diajukan"
        )
    )
    if p is not None:
        if p.mode == "alurkerja" and p.alurkerja_instance_id:
            klien = _klien()
            try:
                if klien is None:
                    raise AlurKerjaGalat("AlurKerja tidak dikonfigurasi.")
                klien.ganti_penerima(p.alurkerja_instance_id, _email(db, body.dosen_id) or "", TUGAS_TINJAU, "pembimbing")
            except AlurKerjaGalat as exc:
                db.rollback()
                log.error("Gagal mengalihkan tugas judul %s: %s", p.id, exc)
                raise galat(502, "Pengajuan yang berjalan belum dapat dialihkan di AlurKerja. Coba lagi.") from None
        p.pembimbing_id = body.dosen_id
    audit.catat(
        db, saya.orang_id, "pembimbing_ta.tunjuk", "pembimbing_ta", baru.id,
        {"dosen_id": str(lama.dosen_id)} if lama else None,
        {"mahasiswa_id": str(body.mahasiswa_id), "dosen_id": str(body.dosen_id)},
    )
    db.commit()
    return {"pembimbing": _orang(db, body.dosen_id)}


# ------------------------------------------------------------------ pengajuan
def _isi(p: PengajuanJudul, body: JudulIn) -> None:
    p.topik, p.judul, p.deskripsi, p.metodologi = body.topik, body.judul, body.deskripsi, body.metodologi
    p.tema = body.tema
    p.keywords = list(body.keywords)
    p.referensi = [r.model_dump() for r in body.referensi]


@router.post("/pengajuan-judul", status_code=201)
def ajukan(body: JudulIn, saya: Saya, db: DB, hari: Hari) -> dict:
    prodi_id = _prodi_mahasiswa(saya)
    if body.pembimbing_id:
        tersedia = {o.id for o in _dosen_prodi(db, prodi_id, hari) if o.id != saya.orang_id}
        if body.pembimbing_id not in tersedia:
            raise galat(400, "Pilih dosen pembimbing aktif dari program studi Anda.")
        pembimbing_id = body.pembimbing_id
    else:
        pb = _pembimbing_aktif(db, saya.orang_id)
        if pb is None:
            raise galat(409, "Pilih dosen pembimbing sebelum mengajukan judul.")
        pembimbing_id = pb.dosen_id
    email = _email(db, pembimbing_id)
    if not email:
        raise galat(409, "Dosen pembimbing yang dipilih belum memiliki akun aktif.")
    klien = _klien()
    prodi = db.get(Prodi, prodi_id)
    p = PengajuanJudul(
        mahasiswa_id=saya.orang_id, pembimbing_id=pembimbing_id, prodi_id=prodi_id,
        mode="alurkerja" if klien else "lokal", tahap="tinjau", jumlah_revisi=0,
    )
    _isi(p, body)
    db.add(p)
    db.flush()  # indeks "satu pengajuan terbuka" ditegakkan sebelum AlurKerja dihubungi

    if klien:
        s = get_settings()
        try:
            p.alurkerja_instance_id = klien.mulai(
                business_key=str(p.id),
                variabel={
                    "pembimbing": email,
                    "initiator": s.alurkerja_initiator or klien.username,
                    # Nama mahasiswa sengaja tidak dikirim ke AlurKerja (hanya NIM).
                    "nim_mahasiswa": saya.orang.nim or "",
                    "id_pengajuan": str(p.id),
                    "prodi": prodi.nama if prodi else "",
                    "topik": p.topik,
                    "judul": p.judul,
                    "tema": p.tema,
                    "ringkasan_judul": ringkasan_judul(p, prodi.nama if prodi else ""),
                    "jumlah_revisi": 0,
                },
            )
        except AlurKerjaGalat as exc:
            db.rollback()
            log.error("Gagal memulai proses judul: %s", exc)
            raise galat(502, "Pengajuan belum dapat diteruskan ke AlurKerja. Coba lagi beberapa saat lagi.") from None
    audit.catat(
        db, saya.orang_id, "judul.ajukan", "pengajuan_judul", p.id, None,
        {"pembimbing_id": str(pembimbing_id), "mode": p.mode, "alurkerja_instance_id": p.alurkerja_instance_id},
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        if klien and p.alurkerja_instance_id:
            try:
                klien.batalkan(p.alurkerja_instance_id)
            except AlurKerjaGalat:
                log.error("Proses judul yatim: %s", p.alurkerja_instance_id)
        raise
    return _keluaran(db, p)


@router.get("/pengajuan-judul")
def daftar(saya: Saya, db: DB, hal: Hal, status: str | None = None, pembimbing_id: uuid.UUID | None = None) -> dict:
    q = select(PengajuanJudul)
    kondisi = _terlihat(saya)
    if kondisi is not None:
        q = q.where(kondisi)
    if status:
        q = q.where(PengajuanJudul.status == status)
    if pembimbing_id:
        q = q.where(PengajuanJudul.pembimbing_id == pembimbing_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(PengajuanJudul.diajukan_pada.desc()).offset(hal.offset).limit(hal.ukuran)).all()
    berubah = False
    for p in [r for r in rows if r.status == "diajukan"][:20]:
        berubah |= _sinkron(db, p)
    if berubah:
        db.commit()
    return {"data": [_keluaran(db, p) for p in rows], "total": total}


@router.get("/pengajuan-judul/{pid}")
def ambil(pid: uuid.UUID, saya: Saya, db: DB) -> dict:
    p = _muat(db, saya, pid)
    if _sinkron(db, p):
        db.commit()
    return _keluaran(db, p)


@router.put("/pengajuan-judul/{pid}")
def ajukan_perbaikan(pid: uuid.UUID, body: JudulIn, saya: Saya, db: DB) -> dict:
    """Mahasiswa mengirim judul hasil perbaikan setelah pembimbing meminta revisi."""
    p = _muat(db, saya, pid)
    if p.mahasiswa_id != saya.orang_id:
        raise dilarang("Hanya pengaju yang dapat memperbaiki judul.")
    if _sinkron(db, p):
        db.commit()
    if p.status != "diajukan" or p.tahap != "perbaikan":
        raise galat(409, "Pengajuan ini tidak sedang menunggu perbaikan Anda.")
    sebelum = {"judul": p.judul}
    _isi(p, body)
    p.jumlah_revisi += 1
    prodi = db.get(Prodi, p.prodi_id)
    _selesaikan(p, TUGAS_PERBAIKI, {
        "topik": p.topik,
        "judul": p.judul,
        "tema": p.tema,
        "ringkasan_judul": ringkasan_judul(p, prodi.nama if prodi else ""),
        "jumlah_revisi": p.jumlah_revisi,
    })
    p.tahap = "tinjau"
    audit.catat(db, saya.orang_id, "judul.perbaiki", "pengajuan_judul", p.id, sebelum, {"judul": p.judul})
    db.commit()
    return _keluaran(db, p)


@router.post("/pengajuan-judul/{pid}/keputusan")
def putuskan(pid: uuid.UUID, body: KeputusanJudulIn, saya: Saya, db: DB) -> dict:
    p = _muat(db, saya, pid)
    if p.pembimbing_id != saya.orang_id and not saya.superadmin:
        raise dilarang("Hanya pembimbing tugas akhir yang ditunjuk yang dapat memutuskan.")
    if _sinkron(db, p):
        db.commit()
    if p.status != "diajukan" or p.tahap != "tinjau":
        raise galat(409, "Pengajuan ini tidak sedang menunggu keputusan pembimbing.")
    catatan = (body.catatan or "").strip() or None
    if body.keputusan == "revisi" and not catatan:
        raise galat(400, "Catatan wajib diisi untuk meminta revisi.")
    _selesaikan(p, TUGAS_TINJAU, {"keputusan": body.keputusan, "catatan_dosen": catatan or ""})
    if body.keputusan == "revisi":
        p.tahap, p.catatan = "perbaikan", catatan
    else:
        p.status, p.tahap, p.catatan = "disetujui", "selesai", catatan
        p.diputuskan_pada = datetime.now(UTC)
    audit.catat(
        db, saya.orang_id, f"judul.{'minta_revisi' if body.keputusan == 'revisi' else 'disetujui'}",
        "pengajuan_judul", p.id, None, {"catatan": catatan},
    )
    db.commit()
    return _keluaran(db, p)


def _batalkan(db: Session, p: PengajuanJudul, pelaku: uuid.UUID | None, alasan: str | None) -> None:
    if p.mode == "alurkerja" and p.alurkerja_instance_id:
        klien = _klien()
        try:
            if klien is None:
                raise AlurKerjaGalat("AlurKerja tidak dikonfigurasi.")
            klien.batalkan(p.alurkerja_instance_id)
        except AlurKerjaGalat as exc:
            log.error("Gagal membatalkan proses judul %s: %s", p.alurkerja_instance_id, exc)
            raise galat(502, "Pengajuan judul belum dapat dibatalkan di AlurKerja. Coba lagi.") from None
    p.status = "dibatalkan"
    p.catatan = alasan or p.catatan
    p.diputuskan_pada = datetime.now(UTC)
    audit.catat(db, pelaku, "judul.dibatalkan", "pengajuan_judul", p.id, None, {"alasan": alasan})


@router.post("/pengajuan-judul/{pid}/batalkan")
def batalkan(pid: uuid.UUID, saya: Saya, db: DB) -> dict:
    p = _muat(db, saya, pid)
    if p.mahasiswa_id != saya.orang_id and not saya.superadmin:
        raise dilarang("Hanya pengaju yang dapat membatalkan pengajuan.")
    if _sinkron(db, p):
        db.commit()
    if p.status != "diajukan":
        raise galat(409, f"Pengajuan sudah {p.status}.")
    _batalkan(db, p, saya.orang_id, None)
    db.commit()
    return _keluaran(db, p)


def batalkan_judul_terbuka(db: Session, pelaku_id: uuid.UUID | None, mahasiswa_id: uuid.UUID, alasan: str) -> None:
    """Dipakai saat mahasiswa lulus, keluar, atau pindah prodi."""
    p = db.scalar(
        select(PengajuanJudul).where(PengajuanJudul.mahasiswa_id == mahasiswa_id, PengajuanJudul.status == "diajukan")
    )
    if p is not None:
        _batalkan(db, p, pelaku_id, alasan)
