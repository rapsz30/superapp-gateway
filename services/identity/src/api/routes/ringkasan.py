"""Ringkasan statistik untuk beranda admin (superadmin, dekan, kajur, kaprodi)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from src.api.deps import DB, Hari, Pengguna, Saya
from src.api.errors import dilarang
from src.domain.cakupan import orang_terlihat, penugasan_aktif
from src.domain.prodi_terbuka import prodi_terbuka
from src.models import (
    STATUS_KEANGGOTAAN,
    STATUS_PENGAJUAN,
    Akun,
    Bimbingan,
    Fakultas,
    Jurusan,
    KeanggotaanProdi,
    Orang,
    PanduanAkademik,
    Pengajuan,
    Penugasan,
    Prodi,
)

router = APIRouter(tags=["ringkasan"])

MANAJER = frozenset({"superadmin", "dekan", "kajur", "kaprodi"})
PERAN_HITUNG = ("mahasiswa", "dosen_pa", "kaprodi", "kajur", "dekan")


def hanya_manajer(saya: Saya) -> Pengguna:
    if saya.superadmin or MANAJER.intersection(saya.cakupan.peran):
        return saya
    raise dilarang("Halaman ini untuk superadmin, dekan, kajur, dan kaprodi.")


Manajer = Annotated[Pengguna, Depends(hanya_manajer)]


def _prodi_cakupan(db: Session, saya: Pengguna) -> list[Prodi]:
    q = select(Prodi).where(Prodi.aktif.is_(True)).order_by(Prodi.kode)
    if not saya.superadmin:
        if not saya.cakupan.prodi_ids:
            return []
        q = q.where(Prodi.id.in_(saya.cakupan.prodi_ids))
    return list(db.scalars(q).all())


def _hitung(db: Session, stmt) -> int:
    return int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)


def _label_prodi(p: Prodi) -> dict:
    return {"id": str(p.id), "kode": p.kode, "nama": p.nama}


def _penugasan_n(db: Session, saya: Pengguna, hari, peran: str, prodi_ids: list[uuid.UUID]) -> int:
    cak = saya.cakupan
    q = select(Penugasan).where(Penugasan.peran == peran, penugasan_aktif(hari))
    if saya.superadmin:
        return _hitung(db, q)
    if peran == "dosen_pa":
        kond = []
        if cak.prodi_ids:
            kond.append(and_(Penugasan.unit_tipe == "prodi", Penugasan.unit_id.in_(cak.prodi_ids)))
        if cak.jurusan_ids:
            kond.append(and_(Penugasan.unit_tipe == "jurusan", Penugasan.unit_id.in_(cak.jurusan_ids)))
        if not kond:
            return 0
        return _hitung(db, q.where(or_(*kond)))
    if peran == "kaprodi":
        if not prodi_ids:
            return 0
        return _hitung(db, q.where(Penugasan.unit_tipe == "prodi", Penugasan.unit_id.in_(prodi_ids)))
    if peran == "kajur":
        if not cak.jurusan_ids:
            return 0
        return _hitung(db, q.where(Penugasan.unit_tipe == "jurusan", Penugasan.unit_id.in_(cak.jurusan_ids)))
    if peran == "dekan":
        if not cak.fakultas_ids:
            return 0
        return _hitung(db, q.where(Penugasan.unit_tipe == "fakultas", Penugasan.unit_id.in_(cak.fakultas_ids)))
    return 0


@router.get("/ringkasan")
def ambil_ringkasan(saya: Manajer, db: DB, hari: Hari) -> dict:
    """Agregat KPI, kesehatan data, dan data grafik untuk beranda admin."""
    cak = saya.cakupan
    prodi_list = _prodi_cakupan(db, saya)
    prodi_ids = [p.id for p in prodi_list]
    prodi_map = {p.id: p for p in prodi_list}

    if saya.superadmin:
        fakultas_n = _hitung(db, select(Fakultas).where(Fakultas.aktif.is_(True)))
        jurusan_n = _hitung(db, select(Jurusan).where(Jurusan.aktif.is_(True)))
    elif cak.fakultas_ids:
        fakultas_n = len(cak.fakultas_ids)
        jurusan_n = len(cak.jurusan_ids)
    elif prodi_ids:
        jur_ids = set(db.scalars(select(Prodi.jurusan_id).where(Prodi.id.in_(prodi_ids))).all())
        fak_ids = set(db.scalars(select(Jurusan.fakultas_id).where(Jurusan.id.in_(jur_ids))).all()) if jur_ids else set()
        fakultas_n = len(fak_ids)
        jurusan_n = len(jur_ids)
    else:
        fakultas_n = 0
        jurusan_n = len(cak.jurusan_ids)

    terlihat = orang_terlihat(db, cak, hari)
    orang_q = select(Orang.id)
    if terlihat is not None:
        orang_q = orang_q.where(Orang.id.in_(select(terlihat.c[0])))
    orang_n = _hitung(db, orang_q)
    orang_ids_sub = orang_q.subquery()

    anggota_aktif_q = select(KeanggotaanProdi).where(
        KeanggotaanProdi.selesai.is_(None),
        KeanggotaanProdi.status == "aktif",
    )
    if prodi_ids:
        anggota_aktif_q = anggota_aktif_q.where(KeanggotaanProdi.prodi_id.in_(prodi_ids))
    elif not saya.superadmin:
        anggota_aktif_q = anggota_aktif_q.where(False)
    mahasiswa_aktif = _hitung(db, anggota_aktif_q)

    mhs_ids_q = select(KeanggotaanProdi.orang_id).where(
        KeanggotaanProdi.selesai.is_(None),
        KeanggotaanProdi.status == "aktif",
    )
    if prodi_ids:
        mhs_ids_q = mhs_ids_q.where(KeanggotaanProdi.prodi_id.in_(prodi_ids))
    elif not saya.superadmin:
        mhs_ids_q = mhs_ids_q.where(False)

    bimbingan_aktif = _hitung(
        db,
        select(Bimbingan).where(Bimbingan.selesai.is_(None), Bimbingan.mahasiswa_id.in_(mhs_ids_q)),
    )

    tanpa_dpa_q = select(KeanggotaanProdi.orang_id).where(
        KeanggotaanProdi.selesai.is_(None),
        KeanggotaanProdi.status == "aktif",
        ~KeanggotaanProdi.orang_id.in_(select(Bimbingan.mahasiswa_id).where(Bimbingan.selesai.is_(None))),
    )
    if prodi_ids:
        tanpa_dpa_q = tanpa_dpa_q.where(KeanggotaanProdi.prodi_id.in_(prodi_ids))
    elif not saya.superadmin:
        tanpa_dpa_q = tanpa_dpa_q.where(False)
    mahasiswa_tanpa_dpa = _hitung(db, tanpa_dpa_q)

    dosen_pa_aktif = _penugasan_n(db, saya, hari, "dosen_pa", prodi_ids)
    kaprodi_aktif = _penugasan_n(db, saya, hari, "kaprodi", prodi_ids)

    peran_counts: dict[str, int] = {}
    for peran in PERAN_HITUNG:
        if peran == "mahasiswa":
            peran_counts[peran] = mahasiswa_aktif
            continue
        q = select(Penugasan.orang_id).where(Penugasan.peran == peran, penugasan_aktif(hari)).distinct()
        if terlihat is not None:
            q = q.where(Penugasan.orang_id.in_(select(terlihat.c[0])))
        peran_counts[peran] = _hitung(db, q)

    akun_q = select(Akun).where(Akun.orang_id.in_(select(orang_ids_sub.c[0])))
    dengan_akun = _hitung(db, akun_q)
    tanpa_akun = max(0, orang_n - dengan_akun)
    wajib_ganti = _hitung(
        db,
        select(Akun).where(
            Akun.orang_id.in_(select(orang_ids_sub.c[0])),
            Akun.wajib_ganti_sandi.is_(True),
        ),
    )
    status_akun = {s: 0 for s in ("aktif", "ditangguhkan", "nonaktif")}
    for status, n in db.execute(
        select(Akun.status, func.count())
        .where(Akun.orang_id.in_(select(orang_ids_sub.c[0])))
        .group_by(Akun.status)
    ):
        status_akun[str(status)] = int(n)

    keanggotaan_status = {s: 0 for s in STATUS_KEANGGOTAAN}
    kq = select(KeanggotaanProdi.status, func.count())
    if prodi_ids:
        kq = kq.where(KeanggotaanProdi.prodi_id.in_(prodi_ids))
    elif not saya.superadmin:
        kq = kq.where(False)
    for status, n in db.execute(kq.group_by(KeanggotaanProdi.status)):
        keanggotaan_status[str(status)] = int(n)

    pengajuan_status = {s: 0 for s in STATUS_PENGAJUAN}
    pq = select(Pengajuan.status, func.count())
    if not saya.superadmin:
        if prodi_ids:
            pq = pq.where(
                or_(
                    Pengajuan.prodi_id.in_(prodi_ids),
                    Pengajuan.mahasiswa_id == saya.orang_id,
                    Pengajuan.dpa_id == saya.orang_id,
                )
            )
        else:
            pq = pq.where(
                or_(Pengajuan.mahasiswa_id == saya.orang_id, Pengajuan.dpa_id == saya.orang_id)
            )
    for status, n in db.execute(pq.group_by(Pengajuan.status)):
        pengajuan_status[str(status)] = int(n)

    kaprodi_unit = set(
        db.scalars(
            select(Penugasan.unit_id).where(
                Penugasan.peran == "kaprodi",
                Penugasan.unit_tipe == "prodi",
                penugasan_aktif(hari),
                Penugasan.unit_id.is_not(None),
            )
        ).all()
    )
    # Hanya panduan prodi (bukan pribadi). Prodi dummy tidak dihitung "tanpa panduan".
    panduan_prodi = set(
        db.scalars(
            select(PanduanAkademik.prodi_id).where(
                PanduanAkademik.status == "aktif", PanduanAkademik.pemilik_id.is_(None)
            )
        ).all()
    )
    dummy = prodi_terbuka(db)
    prodi_tanpa_kaprodi = [_label_prodi(p) for p in prodi_list if p.id not in kaprodi_unit]
    prodi_tanpa_panduan = [
        _label_prodi(p)
        for p in prodi_list
        if p.id not in panduan_prodi and (dummy is None or p.id != dummy.id)
    ]

    per_prodi: dict[uuid.UUID, int] = defaultdict(int)
    mpq = select(KeanggotaanProdi.prodi_id, func.count()).where(
        KeanggotaanProdi.selesai.is_(None),
        KeanggotaanProdi.status == "aktif",
    )
    if prodi_ids:
        mpq = mpq.where(KeanggotaanProdi.prodi_id.in_(prodi_ids))
    elif not saya.superadmin:
        mpq = mpq.where(False)
    for pid, n in db.execute(mpq.group_by(KeanggotaanProdi.prodi_id)):
        per_prodi[pid] = int(n)

    mahasiswa_per_prodi = sorted(
        [
            {
                "id": str(pid),
                "kode": prodi_map[pid].kode if pid in prodi_map else "",
                "nama": prodi_map[pid].nama if pid in prodi_map else str(pid),
                "total": total,
            }
            for pid, total in per_prodi.items()
            if pid in prodi_map
        ],
        key=lambda x: (-x["total"], x["nama"]),
    )

    return {
        "struktur": {"fakultas": fakultas_n, "jurusan": jurusan_n, "prodi": len(prodi_list)},
        "orang": orang_n,
        "mahasiswa_aktif": mahasiswa_aktif,
        "dosen_pa_aktif": dosen_pa_aktif,
        "kaprodi_aktif": kaprodi_aktif,
        "bimbingan_aktif": bimbingan_aktif,
        "mahasiswa_tanpa_dpa": mahasiswa_tanpa_dpa,
        "akun": {
            "dengan_akun": dengan_akun,
            "tanpa_akun": tanpa_akun,
            "wajib_ganti_sandi": wajib_ganti,
            "status": status_akun,
        },
        "peran": peran_counts,
        "keanggotaan_status": keanggotaan_status,
        "pengajuan_status": pengajuan_status,
        "prodi_tanpa_kaprodi": prodi_tanpa_kaprodi,
        "prodi_tanpa_panduan": prodi_tanpa_panduan,
        "mahasiswa_per_prodi": mahasiswa_per_prodi,
    }
