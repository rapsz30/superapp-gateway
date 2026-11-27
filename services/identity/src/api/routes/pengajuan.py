"""Pengajuan rencana studi ke dosen pembimbing akademik (DPA) lewat proses AlurKerja lengkap.

Alur (BPMN `perencanaan-studi-superapp`): unggah KHS -> baca KHS (AI) -> [periksa oleh mahasiswa bila keyakinan
< 0,9] -> rekomendasi (AI) -> tinjauan DPA -> [revisi AI -> tinjauan lagi] -> disetujui.

Dua mode, ditentukan konfigurasi AlurKerja:
- alurkerja: proses dijalankan AlurKerja; worker (alurkerja-connector) mengerjakan langkah AI; DPA memutuskan di
  Tasklist. Keadaan dibaca dari AlurKerja saat pengajuan dibuka atau didaftar (lazy sync).
- lokal: tanpa AlurKerja. Identity menjalankan urutan langkah yang sama sendiri (di latar belakang) dan DPA memutuskan
  lewat POST /pengajuan/{id}/keputusan. Untuk pengembangan dan uji.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.api.deps import DB, Hal, Pengguna, Saya
from src.api.errors import dilarang, galat, tidak_ditemukan
from src.api.routes.judul import batalkan_judul_terbuka
from src.api.schemas import KeputusanIn
from src.core.config import get_settings
from src.db import get_sessionmaker
from src.domain import audit
from src.domain.panduan_berlaku import pesan_tanpa_panduan, panduan_berlaku
from src.integrations import alurkerja, matkul
from src.integrations.alurkerja import AlurKerjaGalat, Snapshot, json_atau_nilai
from src.integrations.matkul import MatkulGalat
from src.models import Akun, Bimbingan, Orang, Pengajuan, Prodi

router = APIRouter(tags=["pengajuan"])
log = logging.getLogger("identity.pengajuan")

MAKS_BYTE_PDF = 15 * 1024 * 1024
AMBANG_KEYAKINAN = 0.9  # sama dengan gateway GW_Yakin di BPMN
MAKS_SINKRON_PER_DAFTAR = 20

TAHAP_DARI_AKTIVITAS = {
    "Task_Unggah": "ekstraksi",
    "Task_BacaKhs": "ekstraksi",
    "Task_Periksa": "periksa",
    "Task_Rekom": "rekomendasi",
    "Task_Tinjau": "tinjau",
    "Task_Revisi": "revisi",
    "Task_KirimRencana": "selesai",
    "Task_Catat": "selesai",
    "End_Disetujui": "selesai",
}

# Variabel proses yang disalin ke data_proses (tanpa nama atau NIM mahasiswa).
VARIABEL_DISALIN = (
    "khs_ref", "rencana_ref", "ipk", "sks_lulus", "mk_lulus", "mk_ulang", "keyakinan", "prodi", "nim_cocok",
    "rencana_mk", "total_sks", "alasan", "peringatan", "ada_peringatan", "jumlah_revisi",
)
VARIABEL_DAFTAR = ("mk_lulus", "mk_ulang", "rencana_mk", "peringatan")


def _digits(s: object) -> str:
    return "".join(ch for ch in str(s or "") if ch.isdigit())


def _email_dpa(db: Session, dpa: Orang) -> str | None:
    akun = db.scalar(select(Akun).where(Akun.orang_id == dpa.id))
    return akun.email if akun else dpa.email_kontak


# ------------------------------------------------------------------ keluaran
def _langkah(p: Pengajuan) -> list[dict[str, str]]:
    """Garis waktu tiga langkah untuk tampilan. `keadaan`: selesai, aktif, menunggu, atau galat."""
    indeks = {"ekstraksi": 0, "periksa": 0, "rekomendasi": 1, "tinjau": 2, "revisi": 2, "selesai": 3}[p.tahap]
    dasar = [("ekstraksi", "KHS dikirim"), ("rekomendasi", "Rencana studi disiapkan"), ("tinjau", "Ditinjau pembimbing akademik")]
    hasil = []
    for i, (kunci, label) in enumerate(dasar):
        if p.status == "disetujui" or i < indeks:
            keadaan = "selesai"
        elif p.status == "dibatalkan":
            keadaan = "menunggu"
        elif i == indeks:
            keadaan = "galat" if p.pesan_galat else "aktif"
        else:
            keadaan = "menunggu"
        keterangan = ""
        if i == indeks and p.status == "diajukan":
            if p.tahap == "periksa":
                keterangan = "Menunggu Anda memeriksa hasil bacaan KHS"
            elif p.tahap == "revisi":
                keterangan = "Rencana direvisi sesuai catatan pembimbing"
            elif p.tahap == "tinjau":
                keterangan = "Menunggu keputusan pembimbing akademik"
        hasil.append({"kunci": kunci, "label": label, "keadaan": keadaan, "keterangan": keterangan})
    return hasil


def _keluaran(db: Session, p: Pengajuan, *, rinci: bool) -> dict:
    mhs = db.get(Orang, p.mahasiswa_id)
    dpa = db.get(Orang, p.dpa_id)
    prodi = db.get(Prodi, p.prodi_id)
    panduan_sekarang = panduan_berlaku(db, p.prodi_id, p.mahasiswa_id)
    aktif = panduan_sekarang.versi if panduan_sekarang else None
    d = p.data_proses or {}
    hasil: dict[str, Any] = {
        "id": str(p.id),
        "status": p.status,
        "tahap": p.tahap,
        "langkah": _langkah(p),
        "pesan_galat": p.pesan_galat,
        "mode": p.mode,
        "semester_target": p.semester_target,
        "mahasiswa": {"id": str(mhs.id), "nama_lengkap": mhs.nama_lengkap, "nim": mhs.nim} if mhs else None,
        "dpa": {"id": str(dpa.id), "nama_lengkap": dpa.nama_lengkap} if dpa else None,
        "prodi": {"id": str(prodi.id), "kode": prodi.kode, "nama": prodi.nama} if prodi else None,
        "panduan": {"id": str(p.panduan_id), "versi": p.panduan_versi, "versi_aktif_sekarang": aktif},
        "catatan_dpa": p.catatan_dpa,
        "jumlah_revisi": d.get("jumlah_revisi", 0),
        "diajukan_pada": p.diajukan_pada.isoformat(),
        "diputuskan_pada": p.diputuskan_pada.isoformat() if p.diputuskan_pada else None,
    }
    if rinci:
        hasil["hasil_bacaan"] = {
            k: d.get(k) for k in ("ipk", "sks_lulus", "mk_ulang", "keyakinan", "nim_cocok") if k in d
        }
        hasil["rencana"] = {k: d.get(k) for k in ("rencana_mk", "total_sks", "alasan", "peringatan") if k in d} or None
    return hasil


# ------------------------------------------------------------------ sinkron dari AlurKerja
def _terapkan_snapshot(p: Pengajuan, snap: Snapshot) -> bool:
    """Salin keadaan proses ke baris pengajuan. True bila ada yang berubah."""
    sebelum = (p.status, p.tahap, dict(p.data_proses or {}), p.catatan_dpa, p.pesan_galat)

    data = dict(p.data_proses or {})
    for k in VARIABEL_DISALIN:
        if k in snap.variabel and snap.variabel[k] is not None:
            nilai = snap.variabel[k]
            data[k] = json_atau_nilai(nilai) if k in VARIABEL_DAFTAR else nilai
    p.data_proses = data

    keputusan = snap.variabel.get("keputusan")
    catatan = snap.variabel.get("catatan_dosen")
    if keputusan == "revisi" and catatan:
        p.catatan_dpa = str(catatan)

    if snap.selesai:
        if snap.state == "COMPLETED" and keputusan == "setuju":
            p.status, p.tahap = "disetujui", "selesai"
            p.diputuskan_pada = p.diputuskan_pada or datetime.now(UTC)
            if catatan:
                p.catatan_dpa = str(catatan)
        else:
            # Dihentikan dari AlurKerja (atau hilang) tanpa keputusan setuju.
            p.status = "dibatalkan"
            p.catatan_dpa = p.catatan_dpa or f"Proses di AlurKerja berakhir ({snap.state})."
            p.diputuskan_pada = p.diputuskan_pada or datetime.now(UTC)
        p.pesan_galat = None
    else:
        for aktivitas in snap.aktif:
            if aktivitas in TAHAP_DARI_AKTIVITAS:
                p.tahap = TAHAP_DARI_AKTIVITAS[aktivitas]
                break
        p.pesan_galat = snap.galat
    return sebelum != (p.status, p.tahap, dict(p.data_proses or {}), p.catatan_dpa, p.pesan_galat)


def _sinkron(db: Session, p: Pengajuan) -> bool:
    """Baca keadaan proses dari AlurKerja untuk pengajuan terbuka. Galat jaringan tidak mengubah apa pun."""
    if p.status != "diajukan" or p.mode != "alurkerja" or not p.alurkerja_instance_id:
        return False
    klien = alurkerja.dapatkan_klien()
    if klien is None:
        return False
    try:
        snap = klien.snapshot(p.alurkerja_instance_id)
    except AlurKerjaGalat as exc:
        log.warning("Sinkron AlurKerja gagal untuk pengajuan %s: %s", p.id, exc)
        return False
    sebelum_status = p.status
    berubah = _terapkan_snapshot(p, snap)
    if berubah and p.status != sebelum_status:
        audit.catat(db, None, f"pengajuan.{p.status}", "pengajuan", p.id, {"status": sebelum_status}, {"status": p.status})
    return berubah


# ------------------------------------------------------------------ mode lokal (tanpa AlurKerja)
def _simpan_hasil_ekstraksi(p: Pengajuan, h: dict[str, Any]) -> None:
    d = dict(p.data_proses or {})
    for k in ("khs_ref", "ipk", "sks_lulus", "mk_lulus", "mk_ulang", "keyakinan", "prodi"):
        d[k] = h.get(k)
    d["nim_cocok"] = h.get("nim_cocok", True)
    p.data_proses = d


def _simpan_hasil_rencana(p: Pengajuan, h: dict[str, Any], jumlah_revisi: int) -> None:
    d = dict(p.data_proses or {})
    d.update(
        rencana_ref=h["rencana_ref"],
        rencana_mk=h["rencana_mk"],
        total_sks=h["total_sks"],
        alasan=h["alasan"],
        peringatan=h["peringatan"],
        ada_peringatan=bool(h["peringatan"]),
        jumlah_revisi=jumlah_revisi,
    )
    p.data_proses = d


def _jalankan_lokal(pengajuan_id: uuid.UUID, langkah: str, catatan: str | None = None) -> None:
    """Urutan langkah yang sama dengan BPMN, dijalankan di latar belakang. Galat disimpan sebagai pesan_galat."""
    with get_sessionmaker()() as db:
        p = db.get(Pengajuan, pengajuan_id)
        if p is None or p.status != "diajukan":
            return
        try:
            klien = matkul.dapatkan_matkul()
            d = p.data_proses or {}
            if langkah == "ekstraksi":
                h = klien.ekstraksi(p.khs_file_id or "", p.semester_target, str(p.id))
                _simpan_hasil_ekstraksi(p, h)
                yakin = float(h.get("keyakinan") or 0) >= AMBANG_KEYAKINAN
                p.tahap = "rekomendasi" if yakin else "periksa"
                db.commit()
                langkah = "rekomendasi" if yakin else ""
            if langkah == "rekomendasi":
                h = klien.rekomendasi(str(p.data_proses["khs_ref"]), p.semester_target)
                _simpan_hasil_rencana(p, h, 0)
                p.tahap = "tinjau"
            elif langkah == "revisi":
                h = klien.revisi(str(d["rencana_ref"]), catatan or "")
                _simpan_hasil_rencana(p, h, int(d.get("jumlah_revisi") or 0) + 1)
                p.tahap = "tinjau"
            p.pesan_galat = None
        except (MatkulGalat, KeyError) as exc:
            log.error("Langkah lokal %s gagal untuk pengajuan %s: %s", langkah, pengajuan_id, exc)
            p.pesan_galat = f"Langkah {langkah or 'proses'} gagal: {exc}"
        db.commit()


# ------------------------------------------------------------------ rute
def _terlihat(saya: Pengguna):
    cak = saya.cakupan
    if cak.superadmin:
        return None
    kondisi = [Pengajuan.mahasiswa_id == saya.orang_id, Pengajuan.dpa_id == saya.orang_id]
    if cak.prodi_ids:
        kondisi.append(Pengajuan.prodi_id.in_(cak.prodi_ids))
    return or_(*kondisi)


def _muat(db: Session, saya: Pengguna, pid: uuid.UUID) -> Pengajuan:
    q = select(Pengajuan).where(Pengajuan.id == pid)
    kondisi = _terlihat(saya)
    if kondisi is not None:
        q = q.where(kondisi)
    p = db.scalar(q)
    if p is None:
        raise tidak_ditemukan("Pengajuan")
    return p


@router.post("/pengajuan", status_code=201)
def ajukan(
    saya: Saya,
    db: DB,
    background: BackgroundTasks,
    semester_target: int = Form(..., ge=1, le=14),
    berkas: UploadFile = File(...),
) -> dict:
    """Mulai pengajuan: unggah KHS (PDF) dan semester tujuan. Seluruh langkah AI dijalankan proses AlurKerja."""
    cak = saya.cakupan
    if cak.prodi_mahasiswa is None:
        raise dilarang("Hanya mahasiswa yang dapat mengajukan rencana studi.")

    isi = berkas.file.read(MAKS_BYTE_PDF + 1)
    if len(isi) > MAKS_BYTE_PDF:
        raise galat(413, "Ukuran KHS maksimal 15 MB.")
    if not isi.startswith(b"%PDF-"):
        raise galat(400, "KHS harus berupa PDF.")

    panduan = panduan_berlaku(db, cak.prodi_mahasiswa, saya.orang_id)
    if panduan is None:
        prodi = db.get(Prodi, cak.prodi_mahasiswa)
        nama = prodi.nama if prodi else "Anda"
        raise galat(409, pesan_tanpa_panduan(db, cak.prodi_mahasiswa, nama))
    dpa = db.scalar(
        select(Orang)
        .join(Bimbingan, Bimbingan.dosen_id == Orang.id)
        .where(Bimbingan.mahasiswa_id == saya.orang_id, Bimbingan.selesai.is_(None))
    )
    if dpa is None:
        raise galat(409, "Anda belum memiliki dosen pembimbing akademik. Hubungi kaprodi.")
    email_dpa = _email_dpa(db, dpa)
    if not email_dpa:
        raise galat(409, "Dosen pembimbing akademik Anda belum memiliki akun. Hubungi admin.")

    klien = alurkerja.dapatkan_klien()
    p = Pengajuan(
        mahasiswa_id=saya.orang_id,
        dpa_id=dpa.id,
        prodi_id=cak.prodi_mahasiswa,
        panduan_id=panduan.id,
        panduan_versi=panduan.versi,
        semester_target=semester_target,
        mode="alurkerja" if klien else "lokal",
        tahap="ekstraksi",
    )
    db.add(p)
    db.flush()  # indeks "satu pengajuan terbuka" ditegakkan di sini, sebelum layanan lain dihubungi

    try:
        p.khs_file_id = matkul.dapatkan_matkul().upload(isi, berkas.filename or "khs.pdf")
    except MatkulGalat as exc:
        db.rollback()
        log.error("Upload KHS ke matkul gagal: %s", exc)
        raise galat(502, "Layanan rekomendasi belum dapat dihubungi. Coba lagi beberapa saat lagi.") from None

    if klien:
        s = get_settings()
        prodi = db.get(Prodi, cak.prodi_mahasiswa)
        try:
            p.alurkerja_instance_id = klien.mulai(
                business_key=str(p.id),
                variabel={
                    # Camunda memakai email sebagai id pengguna dan membedakan huruf besar-kecil.
                    "dosen_pa": email_dpa.strip().lower(),
                    "initiator": s.alurkerja_initiator or klien.username,
                    # Nama mahasiswa sengaja tidak dikirim ke AlurKerja (hanya NIM).
                    "nim_mahasiswa": saya.orang.nim or "",
                    "id_pengajuan": str(p.id),
                    "khs_file_id": p.khs_file_id,
                    "semester_target": semester_target,
                    "program_studi": prodi.nama if prodi else "",
                    "versi_panduan": panduan.versi,
                },
            )
            # Tugas "Unggah KHS & pilih semester" milik mahasiswa; diselesaikan atas namanya.
            klien.selesaikan_tugas(
                p.alurkerja_instance_id, "Task_Unggah", {"khs_file_id": p.khs_file_id, "semester_target": semester_target}
            )
        except AlurKerjaGalat as exc:
            db.rollback()
            if p.alurkerja_instance_id:  # jangan tinggalkan proses yatim
                try:
                    klien.batalkan(p.alurkerja_instance_id)
                except AlurKerjaGalat:
                    log.error("Proses AlurKerja yatim: %s", p.alurkerja_instance_id)
            log.error("Gagal memulai proses AlurKerja: %s", exc)
            raise galat(502, "Pengajuan belum dapat diteruskan ke AlurKerja. Coba lagi beberapa saat lagi.") from None

    audit.catat(
        db, saya.orang_id, "pengajuan.ajukan", "pengajuan", p.id, None,
        {"dpa_id": str(dpa.id), "panduan_versi": panduan.versi, "mode": p.mode, "semester_target": semester_target,
         "alurkerja_instance_id": p.alurkerja_instance_id},
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        if klien and p.alurkerja_instance_id:
            try:
                klien.batalkan(p.alurkerja_instance_id)
            except AlurKerjaGalat:
                log.error("Proses AlurKerja yatim: %s", p.alurkerja_instance_id)
        raise

    if not klien:
        background.add_task(_jalankan_lokal, p.id, "ekstraksi")
    return _keluaran(db, p, rinci=True)


@router.get("/pengajuan")
def daftar(
    saya: Saya,
    db: DB,
    hal: Hal,
    status: str | None = None,
    mahasiswa_id: uuid.UUID | None = None,
    dpa_id: uuid.UUID | None = None,
    prodi_id: uuid.UUID | None = None,
) -> dict:
    q = select(Pengajuan)
    kondisi = _terlihat(saya)
    if kondisi is not None:
        q = q.where(kondisi)
    if status:
        q = q.where(Pengajuan.status == status)
    if mahasiswa_id:
        q = q.where(Pengajuan.mahasiswa_id == mahasiswa_id)
    if dpa_id:
        q = q.where(Pengajuan.dpa_id == dpa_id)
    if prodi_id:
        q = q.where(Pengajuan.prodi_id == prodi_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Pengajuan.diajukan_pada.desc()).offset(hal.offset).limit(hal.ukuran)).all()

    berubah = False
    for p in [r for r in rows if r.status == "diajukan"][:MAKS_SINKRON_PER_DAFTAR]:
        berubah |= _sinkron(db, p)
    if berubah:
        db.commit()
    return {"data": [_keluaran(db, p, rinci=False) for p in rows], "total": total}


# Harus didaftarkan sebelum "/pengajuan/{pid}" agar tidak terbaca sebagai id.
@router.get("/pengajuan/ringkasan-saya")
def ringkasan_saya(saya: Saya, db: DB) -> dict:
    """Ringkasan nilai dari KHS terbaru milik pengguna sendiri, untuk dasbor mahasiswa.

    Pengajuan yang dibatalkan dan KHS yang NIM-nya bukan milik pengguna tidak dihitung. Daftar nilai hanya
    diberikan kepada pemiliknya.
    """
    rows = db.scalars(
        select(Pengajuan)
        .where(Pengajuan.mahasiswa_id == saya.orang_id, Pengajuan.status != "dibatalkan")
        .order_by(Pengajuan.diajukan_pada.desc())
        .limit(MAKS_SINKRON_PER_DAFTAR)
    ).all()
    for p in rows:
        if _sinkron(db, p):
            db.commit()
        d = p.data_proses or {}
        if p.status == "dibatalkan" or not d.get("khs_ref"):
            continue
        try:
            ringkasan = matkul.dapatkan_matkul().ringkasan_khs(str(d["khs_ref"]))
        except MatkulGalat as exc:
            log.error("Ringkasan nilai pengajuan %s gagal: %s", p.id, exc)
            raise galat(502, "Ringkasan nilai belum dapat dimuat. Coba lagi beberapa saat lagi.") from None
        return {
            "ringkasan": ringkasan,
            "sumber": {
                "pengajuan_id": str(p.id),
                "semester_target": p.semester_target,
                "diajukan_pada": p.diajukan_pada.isoformat(),
            },
        }
    return {"ringkasan": None, "sumber": None}


@router.get("/pengajuan/{pid}")
def ambil(pid: uuid.UUID, saya: Saya, db: DB) -> dict:
    p = _muat(db, saya, pid)
    if _sinkron(db, p):
        db.commit()
    return _keluaran(db, p, rinci=True)


@router.post("/pengajuan/{pid}/periksa")
def periksa(pid: uuid.UUID, saya: Saya, db: DB, background: BackgroundTasks) -> dict:
    """Mahasiswa menyatakan hasil bacaan KHS sudah benar (langkah "Periksa" saat keyakinan di bawah 0,9)."""
    p = _muat(db, saya, pid)
    if p.mahasiswa_id != saya.orang_id:
        raise dilarang("Hanya pengaju yang dapat memeriksa hasil bacaan.")
    if _sinkron(db, p):
        db.commit()
    if p.status != "diajukan" or p.tahap != "periksa":
        raise galat(409, "Pengajuan ini tidak sedang menunggu pemeriksaan Anda.")
    if p.mode == "alurkerja":
        klien = alurkerja.dapatkan_klien()
        try:
            if klien is None or not p.alurkerja_instance_id:
                raise AlurKerjaGalat("AlurKerja tidak dikonfigurasi.")
            klien.selesaikan_tugas(p.alurkerja_instance_id, "Task_Periksa", {})
        except AlurKerjaGalat as exc:
            log.error("Gagal menyelesaikan Task_Periksa %s: %s", p.id, exc)
            raise galat(502, "Konfirmasi belum dapat diteruskan ke AlurKerja. Coba lagi beberapa saat lagi.") from None
    else:
        background.add_task(_jalankan_lokal, p.id, "rekomendasi")
    p.tahap = "rekomendasi"
    audit.catat(db, saya.orang_id, "pengajuan.periksa", "pengajuan", p.id)
    db.commit()
    return _keluaran(db, p, rinci=True)


def _batalkan_di_alurkerja(p: Pengajuan) -> None:
    if p.mode != "alurkerja" or not p.alurkerja_instance_id:
        return
    klien = alurkerja.dapatkan_klien()
    if klien is None:
        raise galat(502, "AlurKerja tidak dikonfigurasi, pengajuan tidak dapat dibatalkan.")
    try:
        klien.batalkan(p.alurkerja_instance_id)
    except AlurKerjaGalat as exc:
        log.error("Gagal membatalkan proses %s: %s", p.alurkerja_instance_id, exc)
        raise galat(502, "Pengajuan belum dapat dibatalkan di AlurKerja. Coba lagi beberapa saat lagi.") from None


def _tutup(db: Session, p: Pengajuan, status: str, catatan: str | None, pelaku: uuid.UUID | None) -> None:
    sebelum = {"status": p.status, "catatan_dpa": p.catatan_dpa}
    p.status = status
    if catatan is not None:
        p.catatan_dpa = catatan
    p.pesan_galat = None
    p.diputuskan_pada = datetime.now(UTC)
    if status == "disetujui":
        p.tahap = "selesai"
    audit.catat(db, pelaku, f"pengajuan.{status}", "pengajuan", p.id, sebelum, {"status": status, "catatan_dpa": p.catatan_dpa})


@router.post("/pengajuan/{pid}/batalkan")
def batalkan(pid: uuid.UUID, saya: Saya, db: DB) -> dict:
    p = _muat(db, saya, pid)
    if p.mahasiswa_id != saya.orang_id and not saya.superadmin:
        raise dilarang("Hanya pengaju yang dapat membatalkan pengajuan.")
    if _sinkron(db, p):
        db.commit()
    if p.status != "diajukan":
        raise galat(409, f"Pengajuan sudah {p.status}.")
    _batalkan_di_alurkerja(p)
    _tutup(db, p, "dibatalkan", None, saya.orang_id)
    db.commit()
    return _keluaran(db, p, rinci=False)


@router.post("/pengajuan/{pid}/keputusan")
def putuskan(pid: uuid.UUID, body: KeputusanIn, saya: Saya, db: DB, background: BackgroundTasks) -> dict:
    """Keputusan DPA dari layar aplikasi.

    Mode AlurKerja: identity menyelesaikan tugas `Task_Tinjau` dengan variabel `keputusan` dan `catatan_dosen`
    (sama dengan keluaran form di Tasklist). Hak memutuskan diperiksa di sini, bukan di AlurKerja.
    Mode lokal: langkah berikutnya dijalankan di latar belakang.
    """
    p = _muat(db, saya, pid)
    if p.dpa_id != saya.orang_id and not saya.superadmin:
        raise dilarang("Hanya pembimbing akademik yang ditugaskan yang dapat memutuskan.")
    if _sinkron(db, p):
        db.commit()
    if p.status != "diajukan" or p.tahap != "tinjau":
        raise galat(409, "Pengajuan ini tidak sedang menunggu keputusan pembimbing akademik.")
    catatan = (body.catatan or "").strip() or None
    if body.keputusan == "revisi" and not catatan:
        raise galat(400, "Catatan wajib diisi untuk meminta revisi.")

    if p.mode == "alurkerja":
        klien = alurkerja.dapatkan_klien()
        try:
            if klien is None or not p.alurkerja_instance_id:
                raise AlurKerjaGalat("AlurKerja tidak dikonfigurasi.")
            # catatan_dosen selalu dikirim, supaya catatan revisi sebelumnya tidak tertinggal di proses.
            ada = klien.selesaikan_tugas(
                p.alurkerja_instance_id, "Task_Tinjau", {"keputusan": body.keputusan, "catatan_dosen": catatan or ""}
            )
        except AlurKerjaGalat as exc:
            log.error("Gagal menyelesaikan Task_Tinjau %s: %s", p.id, exc)
            raise galat(502, "Keputusan belum dapat diteruskan ke AlurKerja. Coba lagi beberapa saat lagi.") from None
        if not ada:
            raise galat(409, "Tugas tinjauan sudah tidak terbuka di AlurKerja. Muat ulang halaman.")

    if body.keputusan == "revisi":
        p.catatan_dpa = catatan
        p.tahap = "revisi"
        p.pesan_galat = None
        audit.catat(db, saya.orang_id, "pengajuan.minta_revisi", "pengajuan", p.id, None, {"catatan": catatan})
        db.commit()
        if p.mode == "lokal":
            background.add_task(_jalankan_lokal, p.id, "revisi", catatan)
    else:
        _tutup(db, p, "disetujui", catatan, saya.orang_id)
        db.commit()
    return _keluaran(db, p, rinci=False)


# ------------------------------------------------------------------ dipanggil modul lain
def alihkan_pengajuan_terbuka(db: Session, pelaku_id: uuid.UUID | None, mahasiswa_id: uuid.UUID, dpa_baru_id: uuid.UUID) -> None:
    """Saat DPA mahasiswa berganti, pengajuan yang berjalan ikut pindah ke DPA baru (variabel dan tugas di AlurKerja).

    Bila AlurKerja gagal, seluruh operasi dibatalkan (HTTP 502) agar data lokal dan AlurKerja tidak berbeda.
    """
    p = db.scalar(select(Pengajuan).where(Pengajuan.mahasiswa_id == mahasiswa_id, Pengajuan.status == "diajukan"))
    if p is None or p.dpa_id == dpa_baru_id:
        return
    if p.mode == "alurkerja" and p.alurkerja_instance_id:
        dpa = db.get(Orang, dpa_baru_id)
        email = _email_dpa(db, dpa) if dpa else None
        klien = alurkerja.dapatkan_klien()
        if not email or klien is None:
            raise galat(409, "Dosen pembimbing baru belum memiliki akun, pengajuan yang berjalan tidak dapat dialihkan.")
        try:
            klien.ganti_penerima(p.alurkerja_instance_id, email)
        except AlurKerjaGalat as exc:
            log.error("Gagal mengalihkan tugas %s: %s", p.alurkerja_instance_id, exc)
            raise galat(502, "Pengajuan yang berjalan belum dapat dialihkan di AlurKerja. Coba lagi beberapa saat lagi.") from None
    sebelum = {"dpa_id": str(p.dpa_id)}
    p.dpa_id = dpa_baru_id
    audit.catat(db, pelaku_id, "pengajuan.alihkan_dpa", "pengajuan", p.id, sebelum, {"dpa_id": str(dpa_baru_id)})


def batalkan_pengajuan_terbuka(db: Session, pelaku_id: uuid.UUID | None, mahasiswa_id: uuid.UUID, alasan: str) -> None:
    """Dipakai saat mahasiswa lulus, keluar, atau pindah prodi: pengajuan yang berjalan tidak relevan lagi."""
    batalkan_judul_terbuka(db, pelaku_id, mahasiswa_id, alasan)
    p = db.scalar(select(Pengajuan).where(Pengajuan.mahasiswa_id == mahasiswa_id, Pengajuan.status == "diajukan"))
    if p is None:
        return
    _batalkan_di_alurkerja(p)
    _tutup(db, p, "dibatalkan", alasan, pelaku_id)
