"""Penghitungan peran dan cakupan unit seseorang dari data penugasan yang sedang aktif.

Cakupan selalu dihitung dari database, bukan dipercaya dari token, sehingga perubahan
jabatan langsung berlaku di layanan identity.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from src.models import Bimbingan, Jurusan, KeanggotaanProdi, Orang, Penugasan, Prodi


def penugasan_aktif(hari: date):
    """Aktif pada `hari`. Tanggal selesai bersifat eksklusif: mengakhiri penugasan pada hari X
    membuatnya tidak aktif mulai X, sehingga penggantinya boleh mulai di hari yang sama."""
    return and_(Penugasan.mulai <= hari, or_(Penugasan.selesai.is_(None), Penugasan.selesai > hari))


@dataclass
class Cakupan:
    orang_id: uuid.UUID
    superadmin: bool = False
    peran: list[str] = field(default_factory=list)
    scopes: list[dict[str, Any]] = field(default_factory=list)
    # Unit yang boleh dilihat oleh pemegang jabatan struktural (sudah termasuk turunannya).
    fakultas_ids: set[uuid.UUID] = field(default_factory=set)
    jurusan_ids: set[uuid.UUID] = field(default_factory=set)
    prodi_ids: set[uuid.UUID] = field(default_factory=set)
    # Prodi yang boleh dikelola sebagai kaprodi.
    kaprodi_ids: set[uuid.UUID] = field(default_factory=set)
    dosen_pa: bool = False
    prodi_mahasiswa: uuid.UUID | None = None

    def kelola_prodi(self, prodi_id: uuid.UUID) -> bool:
        return self.superadmin or prodi_id in self.kaprodi_ids

    def lihat_prodi(self, prodi_id: uuid.UUID) -> bool:
        return self.superadmin or prodi_id in self.prodi_ids or prodi_id == self.prodi_mahasiswa

    def lihat_unit(self, tipe: str, unit_id: uuid.UUID | None) -> bool:
        if self.superadmin:
            return True
        if tipe == "fakultas":
            return unit_id in self.fakultas_ids
        if tipe == "jurusan":
            return unit_id in self.jurusan_ids
        if tipe == "prodi":
            return unit_id in self.prodi_ids
        return False


def _prodi_di_jurusan(db: Session, jurusan_id: uuid.UUID) -> set[uuid.UUID]:
    return set(db.scalars(select(Prodi.id).where(Prodi.jurusan_id == jurusan_id)))


def hitung_cakupan(db: Session, orang_id: uuid.UUID, hari: date) -> Cakupan:
    cak = Cakupan(orang_id=orang_id)
    peran: set[str] = set()
    rows = db.scalars(
        select(Penugasan).where(Penugasan.orang_id == orang_id, penugasan_aktif(hari))
    ).all()

    for p in rows:
        peran.add(p.peran)
        if p.peran == "superadmin":
            cak.superadmin = True
            cak.scopes.append({"peran": "superadmin", "tipe": "global"})
            continue
        cak.scopes.append({"peran": p.peran, "tipe": p.unit_tipe, "id": str(p.unit_id)})
        if p.peran == "dekan":
            cak.fakultas_ids.add(p.unit_id)
            jur = set(db.scalars(select(Jurusan.id).where(Jurusan.fakultas_id == p.unit_id)))
            cak.jurusan_ids |= jur
            if jur:
                cak.prodi_ids |= set(db.scalars(select(Prodi.id).where(Prodi.jurusan_id.in_(jur))))
        elif p.peran == "kajur":
            cak.jurusan_ids.add(p.unit_id)
            cak.prodi_ids |= _prodi_di_jurusan(db, p.unit_id)
        elif p.peran == "kaprodi":
            cak.prodi_ids.add(p.unit_id)
            cak.kaprodi_ids.add(p.unit_id)
        elif p.peran == "dosen_pa":
            cak.dosen_pa = True

    anggota = db.scalar(
        select(KeanggotaanProdi).where(
            KeanggotaanProdi.orang_id == orang_id, KeanggotaanProdi.selesai.is_(None)
        )
    )
    if anggota is not None:
        peran.add("mahasiswa")
        cak.prodi_mahasiswa = anggota.prodi_id
        cak.scopes.append({"peran": "mahasiswa", "tipe": "prodi", "id": str(anggota.prodi_id)})

    urutan = ["superadmin", "dekan", "kajur", "kaprodi", "dosen_pa", "mahasiswa"]
    cak.peran = [r for r in urutan if r in peran]
    return cak


def prodi_dicakup_pa(db: Session, orang_id: uuid.UUID, hari: date) -> set[uuid.UUID]:
    """Prodi yang boleh dibimbing seorang dosen PA (unit prodi, atau semua prodi di jurusan)."""
    hasil: set[uuid.UUID] = set()
    rows = db.scalars(
        select(Penugasan).where(
            Penugasan.orang_id == orang_id,
            Penugasan.peran == "dosen_pa",
            penugasan_aktif(hari),
        )
    ).all()
    for p in rows:
        if p.unit_tipe == "prodi":
            hasil.add(p.unit_id)
        elif p.unit_tipe == "jurusan":
            hasil |= _prodi_di_jurusan(db, p.unit_id)
    return hasil


def orang_terlihat(db: Session, cak: Cakupan, hari: date):
    """Kembalikan subquery id orang yang boleh dilihat, atau None bila semua boleh."""
    if cak.superadmin:
        return None
    himpunan: list = [select(Orang.id).where(Orang.id == cak.orang_id)]

    if cak.prodi_ids:
        himpunan.append(
            select(KeanggotaanProdi.orang_id).where(
                KeanggotaanProdi.prodi_id.in_(cak.prodi_ids), KeanggotaanProdi.selesai.is_(None)
            )
        )
    unit_cond = []
    if cak.fakultas_ids:
        unit_cond.append(and_(Penugasan.unit_tipe == "fakultas", Penugasan.unit_id.in_(cak.fakultas_ids)))
    if cak.jurusan_ids:
        unit_cond.append(and_(Penugasan.unit_tipe == "jurusan", Penugasan.unit_id.in_(cak.jurusan_ids)))
    if cak.prodi_ids:
        unit_cond.append(and_(Penugasan.unit_tipe == "prodi", Penugasan.unit_id.in_(cak.prodi_ids)))
    if unit_cond:
        himpunan.append(
            select(Penugasan.orang_id).where(or_(*unit_cond), penugasan_aktif(hari))
        )
    if cak.kaprodi_ids:
        # Kaprodi perlu dapat memilih Dosen PA yang sudah ditugaskan di Prodi lain
        # ketika menambah penugasan dari detail Prodi miliknya sendiri.
        himpunan.append(
            select(Penugasan.orang_id).where(
                Penugasan.peran == "dosen_pa", penugasan_aktif(hari)
            )
        )
    if cak.dosen_pa:
        himpunan.append(
            select(Bimbingan.mahasiswa_id).where(
                Bimbingan.dosen_id == cak.orang_id, Bimbingan.selesai.is_(None)
            )
        )
    if cak.prodi_mahasiswa is not None:
        # Mahasiswa boleh melihat nama dosen PA dan kaprodi prodinya sendiri.
        himpunan.append(
            select(Bimbingan.dosen_id).where(
                Bimbingan.mahasiswa_id == cak.orang_id, Bimbingan.selesai.is_(None)
            )
        )
        himpunan.append(
            select(Penugasan.orang_id).where(
                Penugasan.peran == "kaprodi",
                Penugasan.unit_id == cak.prodi_mahasiswa,
                penugasan_aktif(hari),
            )
        )
    gabungan = himpunan[0]
    if len(himpunan) > 1:
        gabungan = himpunan[0].union(*himpunan[1:])
    return gabungan.subquery()
