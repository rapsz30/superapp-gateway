"""Aturan jumlah dan integritas yang harus ditegakkan database, bukan hanya kode."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from src.models import (
    Bimbingan,
    Fakultas,
    Jurusan,
    KeanggotaanProdi,
    Orang,
    PanduanAkademik,
    Penugasan,
    Prodi,
)

HARI = date(2026, 11, 25)


@pytest.fixture
def unit(db):
    f = Fakultas(kode="F1", nama="F")
    db.add(f)
    db.flush()
    j = Jurusan(fakultas_id=f.id, kode="J1", nama="J")
    db.add(j)
    db.flush()
    p = Prodi(jurusan_id=j.id, kode="P1", nama="P")
    db.add(p)
    db.flush()
    orang = [Orang(nama_lengkap=f"Orang {i}") for i in range(4)]
    db.add_all(orang)
    db.commit()
    return {"f": f, "j": j, "p": p, "o": orang}


def _gagal(db, pesan_bagian: str, aksi):
    with pytest.raises(IntegrityError) as exc:
        aksi()
        db.commit()
    db.rollback()
    assert pesan_bagian in str(exc.value.orig)


@pytest.mark.parametrize(
    ("peran", "tipe", "kunci"),
    [("dekan", "fakultas", "f"), ("kajur", "jurusan", "j"), ("kaprodi", "prodi", "p")],
)
def test_satu_pejabat_aktif_per_unit(db, unit, peran, tipe, kunci):
    uid = unit[kunci].id
    db.add(Penugasan(orang_id=unit["o"][0].id, peran=peran, unit_tipe=tipe, unit_id=uid, mulai=HARI))
    db.commit()
    _gagal(
        db,
        f"uq_{peran}_aktif",
        lambda: db.add(
            Penugasan(orang_id=unit["o"][1].id, peran=peran, unit_tipe=tipe, unit_id=uid, mulai=HARI)
        ),
    )


def test_pejabat_baru_boleh_setelah_yang_lama_diakhiri(db, unit):
    uid = unit["p"].id
    lama = Penugasan(orang_id=unit["o"][0].id, peran="kaprodi", unit_tipe="prodi", unit_id=uid, mulai=HARI)
    db.add(lama)
    db.commit()
    lama.selesai = HARI
    db.add(Penugasan(orang_id=unit["o"][1].id, peran="kaprodi", unit_tipe="prodi", unit_id=uid, mulai=HARI))
    db.commit()


def test_pasangan_peran_dan_unit_dicek(db, unit):
    # kaprodi tidak boleh bertipe jurusan
    _gagal(
        db,
        "ck_penugasan_peran_unit",
        lambda: db.add(
            Penugasan(orang_id=unit["o"][0].id, peran="kaprodi", unit_tipe="jurusan", unit_id=unit["j"].id, mulai=HARI)
        ),
    )
    # unit global tidak boleh punya unit_id
    _gagal(
        db,
        "ck_penugasan_unit_id",
        lambda: db.add(
            Penugasan(orang_id=unit["o"][0].id, peran="superadmin", unit_tipe="global", unit_id=unit["p"].id, mulai=HARI)
        ),
    )


def test_tanggal_selesai_tidak_boleh_sebelum_mulai(db, unit):
    _gagal(
        db,
        "ck_penugasan_tanggal",
        lambda: db.add(
            Penugasan(
                orang_id=unit["o"][0].id, peran="dosen_pa", unit_tipe="prodi", unit_id=unit["p"].id,
                mulai=HARI, selesai=date(2026, 1, 1),
            )
        ),
    )


def test_satu_pa_aktif_per_mahasiswa(db, unit):
    dosen1, dosen2, mhs = unit["o"][0], unit["o"][1], unit["o"][2]
    db.add(Bimbingan(dosen_id=dosen1.id, mahasiswa_id=mhs.id, mulai=HARI))
    db.commit()
    _gagal(db, "uq_bimbingan_aktif", lambda: db.add(Bimbingan(dosen_id=dosen2.id, mahasiswa_id=mhs.id, mulai=HARI)))


def test_dosen_tidak_membimbing_dirinya(db, unit):
    o = unit["o"][0]
    _gagal(db, "ck_bimbingan_diri", lambda: db.add(Bimbingan(dosen_id=o.id, mahasiswa_id=o.id, mulai=HARI)))


def test_satu_keanggotaan_aktif_per_orang(db, unit):
    o = unit["o"][0]
    db.add(KeanggotaanProdi(orang_id=o.id, prodi_id=unit["p"].id, status="aktif", mulai=HARI))
    db.commit()
    _gagal(
        db,
        "uq_keanggotaan_aktif",
        lambda: db.add(KeanggotaanProdi(orang_id=o.id, prodi_id=unit["p"].id, status="cuti", mulai=HARI)),
    )


def test_status_dan_selesai_keanggotaan_konsisten(db, unit):
    o = unit["o"][0]
    # lulus tanpa tanggal selesai ditolak
    _gagal(
        db,
        "ck_keanggotaan_status_selesai",
        lambda: db.add(KeanggotaanProdi(orang_id=o.id, prodi_id=unit["p"].id, status="lulus", mulai=HARI)),
    )


def test_satu_panduan_aktif_per_prodi(db, unit):
    pid = unit["p"].id

    def tambah(versi, status):
        return PanduanAkademik(
            prodi_id=pid, versi=versi, judul="x", status=status, berkas_nama="a.pdf", berkas_path="a"
        )

    db.add(tambah(1, "aktif"))
    db.add(tambah(2, "diarsipkan"))
    db.commit()
    _gagal(db, "uq_panduan_aktif", lambda: db.add(tambah(3, "aktif")))
    _gagal(db, "uq_panduan_versi", lambda: db.add(tambah(1, "draf")))


def test_email_unik_tanpa_beda_huruf(db):
    from src.models import Akun

    a, b = Orang(nama_lengkap="A"), Orang(nama_lengkap="B")
    db.add_all([a, b])
    db.flush()
    db.add(Akun(orang_id=a.id, email="Daffa_PA@gmail.com", sandi_hash="x"))
    db.commit()
    _gagal(db, "uq_akun_email_lower", lambda: db.add(Akun(orang_id=b.id, email="daffa_pa@gmail.com", sandi_hash="x")))


def test_unit_dengan_anak_tidak_bisa_dihapus_fisik(db, unit):
    with pytest.raises(IntegrityError):
        db.execute(text("DELETE FROM fakultas"))
        db.commit()
    db.rollback()


def test_audit_log_hanya_tambah(db):
    db.execute(text("INSERT INTO audit_log (aksi, objek_tipe) VALUES ('uji', 'uji')"))
    db.commit()
    for sql in ("UPDATE audit_log SET aksi = 'ubah'", "DELETE FROM audit_log"):
        with pytest.raises(DBAPIError) as exc:
            db.execute(text(sql))
            db.commit()
        db.rollback()
        assert "hanya-tambah" in str(exc.value.orig)
