"""Penugasan jabatan, keanggotaan prodi (mahasiswa), dan bimbingan dosen PA."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter
from sqlalchemy import and_, func, or_, select

from src.api.deps import DB, Hal, Hari, Pengguna, Saya, Superadmin
from src.api.errors import dilarang, galat, tidak_ditemukan
from src.api.schemas import (
    AkhiriIn,
    BimbinganIn,
    BimbinganOut,
    BimbinganPindahIn,
    DosenProdiIn,
    KeanggotaanIn,
    KeanggotaanOut,
    KeanggotaanPindahIn,
    KeanggotaanStatusIn,
    MahasiswaDummyIn,
    PenugasanIn,
    PenugasanOut,
)
from src.core.config import get_settings
from src.domain import audit
from src.api.routes.pengajuan import alihkan_pengajuan_terbuka, batalkan_pengajuan_terbuka
from src.domain.cakupan import orang_terlihat, penugasan_aktif, prodi_dicakup_pa
from src.domain.mahasiswa_baru import DOMAIN_DUMMY, buat_mahasiswa, nomor_mahasiswa_berikut
from src.domain.prodi_terbuka import adalah_prodi_terbuka, dosen_terbuka
from src.core.security import hash_sandi, validasi_kebijakan_sandi
from src.models import (
    Akun,
    Bimbingan,
    Fakultas,
    Jurusan,
    KeanggotaanProdi,
    Orang,
    Penugasan,
    Prodi,
)

router = APIRouter(tags=["penugasan"])

MODEL_UNIT = {"fakultas": Fakultas, "jurusan": Jurusan, "prodi": Prodi}


# ======================= Penugasan =======================
def _boleh_kelola_penugasan(saya: Pengguna, peran: str, unit_tipe: str, unit_id) -> bool:
    if saya.superadmin:
        return True
    # Kaprodi hanya boleh mengatur dosen PA pada prodinya sendiri.
    return peran == "dosen_pa" and unit_tipe == "prodi" and unit_id in saya.cakupan.kaprodi_ids


@router.post("/prodi/{prodi_id}/dosen", status_code=201)
def buat_dosen_prodi(prodi_id: uuid.UUID, body: DosenProdiIn, saya: Superadmin, db: DB, hari: Hari) -> dict:
    """Buat data dosen, akun login, dan penugasan Dosen PA dalam satu transaksi."""
    prodi = db.get(Prodi, prodi_id)
    if prodi is None or not prodi.aktif:
        raise galat(400, "Prodi tidak ditemukan atau tidak aktif.")
    sandi = body.sandi
    pesan = validasi_kebijakan_sandi(sandi, body.email)
    if pesan:
        raise galat(400, pesan)
    orang = Orang(
        nama_lengkap=body.nama_lengkap,
        nidn=body.nidn,
        email_kontak=body.email_kontak,
    )
    db.add(orang)
    db.flush()
    akun = Akun(orang_id=orang.id, email=body.email, sandi_hash=hash_sandi(sandi), wajib_ganti_sandi=True)
    db.add(akun)
    db.flush()
    penugasan = Penugasan(
        orang_id=orang.id,
        peran="dosen_pa",
        unit_tipe="prodi",
        unit_id=prodi_id,
        mulai=hari,
        dibuat_oleh=saya.orang_id,
    )
    db.add(penugasan)
    db.flush()
    audit.catat(db, saya.orang_id, "orang.buat", "orang", orang.id, None, audit.ke_dict(orang))
    audit.catat(db, saya.orang_id, "akun.buat", "akun", akun.id, None, {"orang_id": str(akun.orang_id), "email": akun.email})
    audit.catat(db, saya.orang_id, "penugasan.buat", "penugasan", penugasan.id, None, audit.ke_dict(penugasan))
    db.commit()
    return {
        "orang": {"id": orang.id, "nama_lengkap": orang.nama_lengkap, "nim": orang.nim, "nidn": orang.nidn, "email_kontak": orang.email_kontak, "peran": ["dosen_pa"], "akun": {"id": akun.id, "email": akun.email, "status": akun.status, "wajib_ganti_sandi": akun.wajib_ganti_sandi}},
        "akun": {"id": akun.id, "orang_id": akun.orang_id, "email": akun.email, "status": akun.status, "wajib_ganti_sandi": akun.wajib_ganti_sandi, "sandi_sementara": None},
        "penugasan": {"id": penugasan.id, "orang_id": penugasan.orang_id, "peran": penugasan.peran, "unit_tipe": penugasan.unit_tipe, "unit_id": penugasan.unit_id, "mulai": penugasan.mulai, "selesai": penugasan.selesai},
    }


@router.get("/penugasan")
def daftar_penugasan(
    saya: Saya,
    db: DB,
    hal: Hal,
    hari: Hari,
    unit_id: uuid.UUID | None = None,
    orang_id: uuid.UUID | None = None,
    peran: str | None = None,
    aktif: bool | None = None,
) -> dict:
    q = select(Penugasan)
    cak = saya.cakupan
    if not cak.superadmin:
        # Hanya penugasan miliknya sendiri atau pada unit dalam cakupannya.
        kondisi = [Penugasan.orang_id == saya.orang_id]
        if cak.fakultas_ids:
            kondisi.append(and_(Penugasan.unit_tipe == "fakultas", Penugasan.unit_id.in_(cak.fakultas_ids)))
        if cak.jurusan_ids:
            kondisi.append(and_(Penugasan.unit_tipe == "jurusan", Penugasan.unit_id.in_(cak.jurusan_ids)))
        if cak.prodi_ids:
            kondisi.append(and_(Penugasan.unit_tipe == "prodi", Penugasan.unit_id.in_(cak.prodi_ids)))
        q = q.where(or_(*kondisi))
    if unit_id:
        q = q.where(Penugasan.unit_id == unit_id)
    if orang_id:
        q = q.where(Penugasan.orang_id == orang_id)
    if peran:
        q = q.where(Penugasan.peran == peran)
    if aktif is True:
        q = q.where(penugasan_aktif(hari))
    elif aktif is False:
        q = q.where(~penugasan_aktif(hari))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Penugasan.mulai.desc()).offset(hal.offset).limit(hal.ukuran)).all()
    return {"data": [PenugasanOut.model_validate(r) for r in rows], "total": total}


@router.post("/penugasan", response_model=PenugasanOut, status_code=201)
def buat_penugasan(body: PenugasanIn, saya: Saya, db: DB, hari: Hari) -> Penugasan:
    if not _boleh_kelola_penugasan(saya, body.peran, body.unit_tipe, body.unit_id):
        raise dilarang()
    orang = db.get(Orang, body.orang_id)
    if orang is None:
        raise galat(400, "Orang tidak ditemukan.")
    if body.unit_tipe != "global":
        unit = db.get(MODEL_UNIT[body.unit_tipe], body.unit_id)
        if unit is None:
            raise galat(400, "Unit tidak ditemukan.")
        if not unit.aktif:
            raise galat(400, "Unit tidak aktif.")
    elif body.peran == "superadmin":
        sudah = db.scalar(
            select(func.count()).select_from(Penugasan).where(
                Penugasan.orang_id == orang.id, Penugasan.peran == "superadmin", Penugasan.selesai.is_(None)
            )
        )
        if sudah:
            raise galat(409, "Orang ini sudah menjadi superadmin aktif.")

    obj = Penugasan(
        orang_id=orang.id,
        peran=body.peran,
        unit_tipe=body.unit_tipe,
        unit_id=body.unit_id,
        mulai=body.mulai or hari,
        dibuat_oleh=saya.orang_id,
    )
    db.add(obj)
    db.flush()
    audit.catat(db, saya.orang_id, "penugasan.buat", "penugasan", obj.id, None, audit.ke_dict(obj))
    db.commit()
    return obj


@router.post("/penugasan/{pid}/akhiri", response_model=PenugasanOut)
def akhiri_penugasan(pid: uuid.UUID, body: AkhiriIn, saya: Saya, db: DB, hari: Hari) -> Penugasan:
    obj = db.get(Penugasan, pid)
    if obj is None:
        raise tidak_ditemukan("Penugasan")
    if not _boleh_kelola_penugasan(saya, obj.peran, obj.unit_tipe, obj.unit_id):
        raise dilarang()
    if obj.selesai is not None and obj.selesai <= hari:
        raise galat(409, "Penugasan ini sudah berakhir.")
    selesai = body.selesai or hari
    if selesai < obj.mulai:
        raise galat(400, "Tanggal selesai tidak boleh sebelum tanggal mulai.")

    if obj.peran == "superadmin":
        lain = db.scalar(
            select(func.count(func.distinct(Penugasan.orang_id)))
            .select_from(Penugasan)
            .join(Akun, Akun.orang_id == Penugasan.orang_id)
            .where(
                Penugasan.peran == "superadmin",
                penugasan_aktif(hari),
                Akun.status == "aktif",
                Penugasan.id != obj.id,
            )
        )
        if not lain:
            raise galat(409, "Tidak boleh mengakhiri superadmin aktif terakhir.")

    if obj.peran == "dosen_pa":
        # Jangan tinggalkan mahasiswa tanpa PA: harus dialihkan lebih dulu.
        penugasan_lain = db.scalar(
            select(func.count()).select_from(Penugasan).where(
                Penugasan.orang_id == obj.orang_id,
                Penugasan.peran == "dosen_pa",
                penugasan_aktif(hari),
                Penugasan.id != obj.id,
            )
        )
        bimbingan_aktif = db.scalar(
            select(func.count()).select_from(Bimbingan).where(
                Bimbingan.dosen_id == obj.orang_id, Bimbingan.selesai.is_(None)
            )
        )
        if bimbingan_aktif and not penugasan_lain:
            raise galat(
                409,
                f"Dosen ini masih membimbing {bimbingan_aktif} mahasiswa. Alihkan bimbingan lebih dulu.",
            )

    sebelum = audit.ke_dict(obj)
    obj.selesai = selesai
    audit.catat(db, saya.orang_id, "penugasan.akhiri", "penugasan", obj.id, sebelum, audit.ke_dict(obj))
    db.commit()
    return obj


# ======================= Keanggotaan prodi =======================
def _muat_keanggotaan(db, kid: uuid.UUID) -> KeanggotaanProdi:
    obj = db.get(KeanggotaanProdi, kid)
    if obj is None:
        raise tidak_ditemukan("Keanggotaan")
    return obj


def _akhiri_bimbingan_mahasiswa(db, saya_id, mahasiswa_id: uuid.UUID, hari: date) -> None:
    for b in db.scalars(
        select(Bimbingan).where(Bimbingan.mahasiswa_id == mahasiswa_id, Bimbingan.selesai.is_(None))
    ):
        sebelum = audit.ke_dict(b)
        b.selesai = max(hari, b.mulai)
        audit.catat(db, saya_id, "bimbingan.akhiri", "bimbingan", b.id, sebelum, audit.ke_dict(b))


@router.get("/keanggotaan")
def daftar_keanggotaan(
    saya: Saya,
    db: DB,
    hal: Hal,
    hari: Hari,
    prodi_id: uuid.UUID | None = None,
    orang_id: uuid.UUID | None = None,
    aktif: bool | None = None,
) -> dict:
    q = select(KeanggotaanProdi)
    terlihat = orang_terlihat(db, saya.cakupan, hari)
    if terlihat is not None:
        q = q.where(KeanggotaanProdi.orang_id.in_(select(terlihat.c[0])))
    if prodi_id:
        q = q.where(KeanggotaanProdi.prodi_id == prodi_id)
    if orang_id:
        q = q.where(KeanggotaanProdi.orang_id == orang_id)
    if aktif is True:
        q = q.where(KeanggotaanProdi.selesai.is_(None))
    elif aktif is False:
        q = q.where(KeanggotaanProdi.selesai.is_not(None))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(KeanggotaanProdi.mulai.desc()).offset(hal.offset).limit(hal.ukuran)).all()
    return {"data": [KeanggotaanOut.model_validate(r) for r in rows], "total": total}


@router.post("/prodi/{pid}/mahasiswa-dummy")
def buat_mahasiswa_dummy(pid: uuid.UUID, body: MahasiswaDummyIn, saya: Superadmin, db: DB, hari: Hari) -> dict:
    """Buat banyak mahasiswa dummy pada prodi terbuka. Hanya superadmin."""
    s = get_settings()
    if body.jumlah > s.dummy_maks_sekali:
        raise galat(400, f"Jumlah maksimal sekali buat adalah {s.dummy_maks_sekali}.")
    prodi = db.get(Prodi, pid)
    if prodi is None:
        raise tidak_ditemukan("Prodi")
    if not adalah_prodi_terbuka(db, pid):
        raise galat(400, "Hanya prodi terbuka (dummy) yang boleh memakai pembuat mahasiswa dummy.")
    dosen = dosen_terbuka(db, prodi, hari)
    if dosen is None:
        raise galat(503, "Prodi terbuka belum siap: dosen PA/kaprodi belum ditetapkan.")
    pesan = validasi_kebijakan_sandi(body.sandi)
    if pesan:
        raise galat(400, pesan)

    sandi_hash = hash_sandi(body.sandi)
    mulai = nomor_mahasiswa_berikut(db)
    akun_keluar: list[dict] = []
    for i in range(body.jumlah):
        nomor = mulai + i
        nama = f"Mahasiswa {nomor:03d}"
        email = f"mahasiswa{nomor}@{DOMAIN_DUMMY}"
        orang, _akun = buat_mahasiswa(
            db,
            nama_lengkap=nama,
            email=email,
            sandi_hash=sandi_hash,
            prodi=prodi,
            dosen_id=dosen.id,
            hari=hari,
            prodi_isian="Program studi dummy",
            pt_isian="Perguruan tinggi dummy",
            pelaku_id=saya.orang_id,
        )
        akun_keluar.append({"nama": orang.nama_lengkap, "email": email})
    db.commit()
    return {"dibuat": len(akun_keluar), "akun": akun_keluar}


@router.post("/keanggotaan", response_model=KeanggotaanOut, status_code=201)
def buat_keanggotaan(body: KeanggotaanIn, saya: Saya, db: DB, hari: Hari) -> KeanggotaanProdi:
    if not saya.cakupan.kelola_prodi(body.prodi_id):
        raise dilarang()
    prodi = db.get(Prodi, body.prodi_id)
    if prodi is None:
        raise galat(400, "Prodi tidak ditemukan.")
    if not prodi.aktif:
        raise galat(400, "Prodi tidak aktif.")
    if db.get(Orang, body.orang_id) is None:
        raise galat(400, "Orang tidak ditemukan.")
    obj = KeanggotaanProdi(
        orang_id=body.orang_id,
        prodi_id=body.prodi_id,
        angkatan=body.angkatan,
        status=body.status,
        mulai=body.mulai or hari,
    )
    db.add(obj)
    db.flush()
    audit.catat(db, saya.orang_id, "keanggotaan.buat", "keanggotaan_prodi", obj.id, None, audit.ke_dict(obj))
    db.commit()
    return obj


@router.post("/keanggotaan/{kid}/status", response_model=KeanggotaanOut)
def ubah_status_keanggotaan(
    kid: uuid.UUID, body: KeanggotaanStatusIn, saya: Saya, db: DB, hari: Hari
) -> KeanggotaanProdi:
    obj = _muat_keanggotaan(db, kid)
    if not saya.cakupan.kelola_prodi(obj.prodi_id):
        raise dilarang()
    if obj.selesai is not None:
        raise galat(409, "Keanggotaan ini sudah berakhir.")
    tanggal = body.tanggal or hari
    sebelum = audit.ke_dict(obj)
    obj.status = body.status
    if body.status in ("lulus", "keluar"):
        if tanggal < obj.mulai:
            raise galat(400, "Tanggal tidak boleh sebelum tanggal mulai.")
        obj.selesai = tanggal
        batalkan_pengajuan_terbuka(db, saya.orang_id, obj.orang_id, f"Mahasiswa {body.status}.")
        _akhiri_bimbingan_mahasiswa(db, saya.orang_id, obj.orang_id, hari)
    audit.catat(db, saya.orang_id, "keanggotaan.status", "keanggotaan_prodi", obj.id, sebelum, audit.ke_dict(obj))
    db.commit()
    return obj


@router.post("/keanggotaan/{kid}/pindah", response_model=KeanggotaanOut)
def pindah_prodi(
    kid: uuid.UUID, body: KeanggotaanPindahIn, saya: Saya, db: DB, hari: Hari
) -> KeanggotaanProdi:
    """Pindah prodi: hanya superadmin. Menutup keanggotaan lama dan bimbingannya, membuka yang baru."""
    if not saya.superadmin:
        raise dilarang()
    lama = _muat_keanggotaan(db, kid)
    if lama.selesai is not None:
        raise galat(409, "Keanggotaan ini sudah berakhir.")
    tujuan = db.get(Prodi, body.prodi_tujuan_id)
    if tujuan is None or not tujuan.aktif:
        raise galat(400, "Prodi tujuan tidak ditemukan atau tidak aktif.")
    if tujuan.id == lama.prodi_id:
        raise galat(400, "Prodi tujuan sama dengan prodi asal.")
    tanggal = max(body.tanggal or hari, lama.mulai)

    sebelum = audit.ke_dict(lama)
    lama.status = "pindah"
    lama.selesai = tanggal
    batalkan_pengajuan_terbuka(db, saya.orang_id, lama.orang_id, "Mahasiswa pindah prodi.")
    _akhiri_bimbingan_mahasiswa(db, saya.orang_id, lama.orang_id, hari)
    db.flush()  # lepaskan indeks keanggotaan aktif sebelum baris baru dibuat
    baru = KeanggotaanProdi(
        orang_id=lama.orang_id,
        prodi_id=tujuan.id,
        angkatan=body.angkatan if body.angkatan is not None else lama.angkatan,
        status="aktif",
        mulai=tanggal,
    )
    db.add(baru)
    db.flush()
    audit.catat(db, saya.orang_id, "keanggotaan.pindah", "keanggotaan_prodi", lama.id, sebelum, audit.ke_dict(lama))
    audit.catat(db, saya.orang_id, "keanggotaan.buat", "keanggotaan_prodi", baru.id, None, audit.ke_dict(baru))
    db.commit()
    return baru


# ======================= Bimbingan =======================
def _anggota_aktif(db, mahasiswa_id: uuid.UUID) -> KeanggotaanProdi:
    a = db.scalar(
        select(KeanggotaanProdi).where(
            KeanggotaanProdi.orang_id == mahasiswa_id, KeanggotaanProdi.selesai.is_(None)
        )
    )
    if a is None:
        raise galat(400, "Mahasiswa tidak terdaftar aktif di prodi mana pun.")
    return a


def _pastikan_dosen_cocok(db, dosen_id: uuid.UUID, prodi_id: uuid.UUID, hari: date) -> None:
    if prodi_id not in prodi_dicakup_pa(db, dosen_id, hari):
        raise galat(400, "Dosen ini tidak memiliki penugasan dosen PA yang mencakup prodi mahasiswa.")


@router.get("/bimbingan")
def daftar_bimbingan(
    saya: Saya,
    db: DB,
    hal: Hal,
    hari: Hari,
    dosen_id: uuid.UUID | None = None,
    mahasiswa_id: uuid.UUID | None = None,
    aktif: bool | None = None,
) -> dict:
    q = select(Bimbingan)
    terlihat = orang_terlihat(db, saya.cakupan, hari)
    if terlihat is not None:
        # Hanya bimbingan yang melibatkan orang yang boleh dilihat (dosen dan mahasiswanya).
        q = q.where(
            Bimbingan.mahasiswa_id.in_(select(terlihat.c[0])),
            Bimbingan.dosen_id.in_(select(terlihat.c[0])),
        )
    if dosen_id:
        q = q.where(Bimbingan.dosen_id == dosen_id)
    if mahasiswa_id:
        q = q.where(Bimbingan.mahasiswa_id == mahasiswa_id)
    if aktif is True:
        q = q.where(Bimbingan.selesai.is_(None))
    elif aktif is False:
        q = q.where(Bimbingan.selesai.is_not(None))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Bimbingan.mulai.desc()).offset(hal.offset).limit(hal.ukuran)).all()
    return {"data": [BimbinganOut.model_validate(r) for r in rows], "total": total}


@router.post("/bimbingan", response_model=BimbinganOut, status_code=201)
def buat_bimbingan(body: BimbinganIn, saya: Saya, db: DB, hari: Hari) -> Bimbingan:
    anggota = _anggota_aktif(db, body.mahasiswa_id)
    if not saya.cakupan.kelola_prodi(anggota.prodi_id):
        raise dilarang()
    _pastikan_dosen_cocok(db, body.dosen_id, anggota.prodi_id, hari)
    obj = Bimbingan(dosen_id=body.dosen_id, mahasiswa_id=body.mahasiswa_id, mulai=body.mulai or hari)
    db.add(obj)
    db.flush()
    audit.catat(db, saya.orang_id, "bimbingan.buat", "bimbingan", obj.id, None, audit.ke_dict(obj))
    alihkan_pengajuan_terbuka(db, saya.orang_id, body.mahasiswa_id, body.dosen_id)
    db.commit()
    return obj


@router.post("/bimbingan/{bid}/akhiri", response_model=BimbinganOut)
def akhiri_bimbingan(bid: uuid.UUID, body: AkhiriIn, saya: Saya, db: DB, hari: Hari) -> Bimbingan:
    obj = db.get(Bimbingan, bid)
    if obj is None:
        raise tidak_ditemukan("Bimbingan")
    anggota = db.scalar(
        select(KeanggotaanProdi)
        .where(KeanggotaanProdi.orang_id == obj.mahasiswa_id)
        .order_by(KeanggotaanProdi.mulai.desc())
    )
    if anggota is None or not saya.cakupan.kelola_prodi(anggota.prodi_id):
        raise dilarang()
    if obj.selesai is not None:
        raise galat(409, "Bimbingan ini sudah berakhir.")
    selesai = body.selesai or hari
    if selesai < obj.mulai:
        raise galat(400, "Tanggal selesai tidak boleh sebelum tanggal mulai.")
    sebelum = audit.ke_dict(obj)
    obj.selesai = selesai
    audit.catat(db, saya.orang_id, "bimbingan.akhiri", "bimbingan", obj.id, sebelum, audit.ke_dict(obj))
    db.commit()
    return obj


@router.post("/bimbingan/pindahkan")
def pindahkan_bimbingan(body: BimbinganPindahIn, saya: Saya, db: DB, hari: Hari) -> dict:
    """Alihkan banyak mahasiswa dari satu dosen PA ke dosen PA lain dalam satu transaksi."""
    if body.dosen_asal_id == body.dosen_tujuan_id:
        raise galat(400, "Dosen asal dan tujuan sama.")
    q = select(Bimbingan).where(Bimbingan.dosen_id == body.dosen_asal_id, Bimbingan.selesai.is_(None))
    if body.mahasiswa_ids is not None:
        q = q.where(Bimbingan.mahasiswa_id.in_(body.mahasiswa_ids))
    lama = db.scalars(q.with_for_update()).all()
    if body.mahasiswa_ids is not None and len(lama) != len(set(body.mahasiswa_ids)):
        raise galat(400, "Sebagian mahasiswa tidak sedang dibimbing dosen asal.")

    # Semua mahasiswa harus di prodi yang boleh dikelola pemanggil dan dicakup dosen tujuan.
    prodi_tujuan = prodi_dicakup_pa(db, body.dosen_tujuan_id, hari)
    pasangan: list[tuple[Bimbingan, KeanggotaanProdi]] = []
    for b in lama:
        anggota = _anggota_aktif(db, b.mahasiswa_id)
        if not saya.cakupan.kelola_prodi(anggota.prodi_id):
            raise dilarang()
        if anggota.prodi_id not in prodi_tujuan:
            raise galat(400, "Dosen tujuan tidak memiliki penugasan dosen PA yang mencakup semua prodi mahasiswa.")
        pasangan.append((b, anggota))

    for b, _ in pasangan:
        sebelum = audit.ke_dict(b)
        b.selesai = max(hari, b.mulai)
        audit.catat(db, saya.orang_id, "bimbingan.akhiri", "bimbingan", b.id, sebelum, audit.ke_dict(b))
    db.flush()
    baru_ids = []
    for b, _ in pasangan:
        nb = Bimbingan(dosen_id=body.dosen_tujuan_id, mahasiswa_id=b.mahasiswa_id, mulai=max(hari, b.mulai))
        db.add(nb)
        db.flush()
        audit.catat(db, saya.orang_id, "bimbingan.buat", "bimbingan", nb.id, None, audit.ke_dict(nb))
        alihkan_pengajuan_terbuka(db, saya.orang_id, b.mahasiswa_id, body.dosen_tujuan_id)
        baru_ids.append(str(nb.id))
    db.commit()
    return {"dialihkan": len(pasangan), "bimbingan_baru": baru_ids}
