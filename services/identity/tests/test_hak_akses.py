"""Matriks hak akses: peran x endpoint, dan penyaringan cakupan unit."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from src.models import Bimbingan, KeanggotaanProdi
from tests.conftest import buat_orang_akun, masuk


def siapkan_dunia(client, db, admin, kampus) -> dict:
    """Kampus berisi: dekan, kajur, kaprodi, dosen PA, dua mahasiswa (satu di tiap prodi),
    dan satu dosen PA + mahasiswa di fakultas lain (untuk uji kebocoran lintas cakupan)."""
    f, j, p1, p2 = kampus["fakultas"], kampus["jurusan"], kampus["prodi1"], kampus["prodi2"]
    fid, jid, p1id, p2id = (uuid.UUID(x["id"]) for x in (f, j, p1, p2))

    dekan = buat_orang_akun(db, "Dekan", "dekan@k.ac.id", peran="dekan", unit_tipe="fakultas", unit_id=fid)
    kajur = buat_orang_akun(db, "Kajur", "kajur@k.ac.id", peran="kajur", unit_tipe="jurusan", unit_id=jid)
    kaprodi = buat_orang_akun(db, "Kaprodi", "kaprodi@k.ac.id", peran="kaprodi", unit_tipe="prodi", unit_id=p1id)
    dosen = buat_orang_akun(db, "Dosen PA", "dosen@k.ac.id", peran="dosen_pa", unit_tipe="prodi", unit_id=p1id)
    mhs = buat_orang_akun(db, "Mahasiswa Satu", "mhs@k.ac.id", nim="20110001")
    mhs2 = buat_orang_akun(db, "Mahasiswa Dua", "mhs2@k.ac.id", nim="20110002")
    db.add_all(
        [
            KeanggotaanProdi(orang_id=mhs.id, prodi_id=p1id, angkatan=2020, status="aktif", mulai=date(2020, 8, 1)),
            KeanggotaanProdi(orang_id=mhs2.id, prodi_id=p2id, angkatan=2021, status="aktif", mulai=date(2021, 8, 1)),
            Bimbingan(dosen_id=dosen.id, mahasiswa_id=mhs.id, mulai=date(2020, 8, 1)),
        ]
    )

    # Fakultas lain, tidak boleh terlihat oleh siapa pun di atas.
    f2 = client.post("/fakultas", json={"kode": "FH", "nama": "Fakultas Hukum"}, headers=admin).json()
    j2 = client.post("/jurusan", json={"fakultas_id": f2["id"], "kode": "HK", "nama": "Hukum"}, headers=admin).json()
    p3 = client.post("/prodi", json={"jurusan_id": j2["id"], "kode": "HK-S1", "nama": "Ilmu Hukum"}, headers=admin).json()
    asing = buat_orang_akun(db, "Mahasiswa Asing", "asing@k.ac.id", nim="99999999")
    db.add(KeanggotaanProdi(orang_id=asing.id, prodi_id=uuid.UUID(p3["id"]), status="aktif", mulai=date(2020, 8, 1)))
    db.commit()

    return {
        "orang": {"dekan": dekan, "kajur": kajur, "kaprodi": kaprodi, "dosen": dosen, "mhs": mhs, "mhs2": mhs2, "asing": asing},
        "h_dekan": masuk(client, "dekan@k.ac.id"),
        "h_kajur": masuk(client, "kajur@k.ac.id"),
        "h_kaprodi": masuk(client, "kaprodi@k.ac.id"),
        "h_dosen": masuk(client, "dosen@k.ac.id"),
        "h_mhs": masuk(client, "mhs@k.ac.id"),
        "h_mhs2": masuk(client, "mhs2@k.ac.id"),
        "prodi3": p3,
        "fakultas2": f2,
    }


@pytest.fixture
def dunia(client, db, admin, kampus):
    return siapkan_dunia(client, db, admin, kampus)


def _nama(client, h, **params):
    r = client.get("/orang", headers=h, params={"ukuran": 200, **params})
    assert r.status_code == 200, r.text
    return {o["nama_lengkap"] for o in r.json()["data"]}


def test_cakupan_orang_per_peran(client, dunia):
    # Pemegang jabatan struktural melihat orang di unitnya, tidak yang di fakultas lain.
    semua_fti = {"Dekan", "Kajur", "Kaprodi", "Dosen PA", "Mahasiswa Satu", "Mahasiswa Dua"}
    assert _nama(client, dunia["h_dekan"]) >= semua_fti
    assert "Mahasiswa Asing" not in _nama(client, dunia["h_dekan"])
    assert "Mahasiswa Asing" not in _nama(client, dunia["h_kajur"])

    # Kaprodi prodi1: mahasiswa prodi1, bukan mahasiswa prodi2.
    kp = _nama(client, dunia["h_kaprodi"])
    assert "Mahasiswa Satu" in kp and "Mahasiswa Dua" not in kp and "Mahasiswa Asing" not in kp

    # Dosen PA: hanya bimbingannya dan dirinya.
    assert _nama(client, dunia["h_dosen"]) == {"Dosen PA", "Mahasiswa Satu"}

    # Mahasiswa: dirinya, PA, dan kaprodi prodinya.
    assert _nama(client, dunia["h_mhs"]) == {"Mahasiswa Satu", "Dosen PA", "Kaprodi"}
    assert _nama(client, dunia["h_mhs2"]) == {"Mahasiswa Dua"}


def test_kaprodi_dapat_memilih_dosen_pa_dari_prodi_lain(client, dunia, db, kampus, admin):
    # Dosen yang baru ditugaskan hanya pada prodi2 tetap harus dapat dipilih
    # dari detail prodi1 untuk skenario penugasan lintas prodi.
    dosen_lintas = buat_orang_akun(db, "Dosen Lintas Prodi", "lintas@k.ac.id")
    db.commit()
    r = client.post(
        "/penugasan",
        json={
            "orang_id": str(dosen_lintas.id),
            "peran": "dosen_pa",
            "unit_tipe": "prodi",
            "unit_id": kampus["prodi2"]["id"],
        },
        headers=admin,
    )
    assert r.status_code == 201, r.text

    hasil = client.get("/orang", headers=dunia["h_kaprodi"], params={"peran": "dosen_pa", "q": "Lintas", "ukuran": 20})
    assert hasil.status_code == 200, hasil.text
    assert {o["nama_lengkap"] for o in hasil.json()["data"]} == {"Dosen Lintas Prodi"}

    # Dari detail prodi1, kaprodi dapat langsung menambahkan dosen yang sudah
    # punya penugasan aktif di prodi2 tanpa memindahkan atau mengakhiri penugasan lama.
    tambah = client.post(
        "/penugasan",
        json={
            "orang_id": str(dosen_lintas.id),
            "peran": "dosen_pa",
            "unit_tipe": "prodi",
            "unit_id": kampus["prodi1"]["id"],
        },
        headers=dunia["h_kaprodi"],
    )
    assert tambah.status_code == 201, tambah.text


def test_orang_di_luar_cakupan_404_bukan_403(client, dunia):
    asing_id = str(dunia["orang"]["asing"].id)
    r = client.get(f"/orang/{asing_id}", headers=dunia["h_dekan"])
    assert r.status_code == 404
    ada = client.get(f"/orang/{dunia['orang']['mhs'].id}", headers=dunia["h_dosen"])
    assert ada.status_code == 200
    # Data akun (email, status) hanya untuk superadmin.
    assert ada.json()["akun"] is None


def test_superadmin_melihat_semua_dan_akun(client, dunia, admin):
    r = client.get("/orang", headers=admin, params={"ukuran": 200}).json()
    assert "Mahasiswa Asing" in {o["nama_lengkap"] for o in r["data"]}
    satu = client.get(f"/orang/{dunia['orang']['mhs'].id}", headers=admin).json()
    assert satu["akun"]["email"] == "mhs@k.ac.id"
    assert "sandi_hash" not in str(satu)


@pytest.mark.parametrize("peran", ["h_dekan", "h_kajur", "h_kaprodi", "h_dosen", "h_mhs"])
def test_hanya_superadmin_menulis_struktur_dan_orang(client, dunia, peran):
    h = dunia[peran]
    assert client.post("/fakultas", json={"kode": "Z", "nama": "Z"}, headers=h).status_code == 403
    assert client.post("/jurusan", json={"fakultas_id": str(uuid.uuid4()), "kode": "Z", "nama": "Z"}, headers=h).status_code == 403
    assert client.post("/prodi", json={"jurusan_id": str(uuid.uuid4()), "kode": "Z", "nama": "Z"}, headers=h).status_code == 403
    assert client.post("/orang", json={"nama_lengkap": "Z"}, headers=h).status_code == 403
    assert client.post("/akun", json={"orang_id": str(uuid.uuid4()), "email": "z@z.ac.id"}, headers=h).status_code == 403
    assert client.get("/audit", headers=h).status_code == 403
    assert client.post(
        "/penugasan",
        json={"orang_id": str(uuid.uuid4()), "peran": "kaprodi", "unit_tipe": "prodi", "unit_id": str(uuid.uuid4())},
        headers=h,
    ).status_code == 403


@pytest.mark.parametrize("peran", ["h_dekan", "h_kajur", "h_kaprodi", "h_dosen", "h_mhs"])
def test_semua_yang_login_boleh_membaca_struktur(client, dunia, peran):
    h = dunia[peran]
    assert client.get("/fakultas", headers=h).status_code == 200
    assert client.get("/jurusan", headers=h).status_code == 200
    assert client.get("/prodi", headers=h).status_code == 200
    assert client.get("/struktur", headers=h).status_code == 200


def test_endpoint_butuh_token(client):
    for jalur in ("/fakultas", "/orang", "/penugasan", "/bimbingan", "/keanggotaan", "/struktur", "/audit"):
        assert client.get(jalur).status_code == 401, jalur


def test_penugasan_dan_bimbingan_tersaring(client, dunia):
    # Dosen PA melihat bimbingan miliknya saja.
    b = client.get("/bimbingan", headers=dunia["h_dosen"]).json()
    assert b["total"] == 1
    # Dekan fakultas lain tidak ada; kaprodi prodi2 tidak melihat bimbingan prodi1 (ditandai lewat mhs2).
    assert client.get("/bimbingan", headers=dunia["h_mhs2"]).json()["total"] == 0
    # Penugasan: dekan melihat jabatan di fakultasnya, tidak di fakultas lain.
    pen = client.get("/penugasan", headers=dunia["h_dekan"]).json()["data"]
    assert pen and all(x["unit_id"] is not None for x in pen)
    assert str(dunia["prodi3"]["id"]) not in {x["unit_id"] for x in pen}
