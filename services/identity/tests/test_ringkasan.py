"""Uji endpoint GET /ringkasan untuk beranda admin."""

from __future__ import annotations

import uuid

from tests.conftest import buat_orang_akun, masuk


def test_ringkasan_superadmin(client, admin, kampus, db):
    mhs = buat_orang_akun(db, "Mhs Satu", "mhs1@k.ac.id", nim="1001")
    client.post(
        "/keanggotaan",
        json={"orang_id": str(mhs.id), "prodi_id": kampus["prodi1"]["id"], "angkatan": 2024},
        headers=admin,
    )
    buat_orang_akun(
        db,
        "Kaprodi Satu",
        "kap1@k.ac.id",
        peran="kaprodi",
        unit_tipe="prodi",
        unit_id=uuid.UUID(kampus["prodi1"]["id"]),
    )

    r = client.get("/ringkasan", headers=admin)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["struktur"]["prodi"] == 2
    assert data["mahasiswa_aktif"] == 1
    assert data["mahasiswa_tanpa_dpa"] == 1
    assert data["kaprodi_aktif"] >= 1
    assert any(p["id"] == kampus["prodi2"]["id"] for p in data["prodi_tanpa_kaprodi"])
    assert kampus["prodi1"]["id"] not in {p["id"] for p in data["prodi_tanpa_kaprodi"]}
    assert data["mahasiswa_per_prodi"][0]["total"] == 1
    assert "diajukan" in data["pengajuan_status"]
    assert data["akun"]["dengan_akun"] >= 1


def test_ringkasan_dilarang_mahasiswa(client, admin, kampus, db):
    mhs = buat_orang_akun(db, "Mhs Biasa", "mhs@k.ac.id", nim="2002")
    client.post(
        "/keanggotaan",
        json={"orang_id": str(mhs.id), "prodi_id": kampus["prodi1"]["id"], "angkatan": 2024},
        headers=admin,
    )
    h = masuk(client, "mhs@k.ac.id")
    assert client.get("/ringkasan", headers=h).status_code == 403


def test_ringkasan_kaprodi_terbatas(client, admin, kampus, db):
    buat_orang_akun(
        db,
        "Kaprodi IF",
        "kaprodi@k.ac.id",
        peran="kaprodi",
        unit_tipe="prodi",
        unit_id=uuid.UUID(kampus["prodi1"]["id"]),
    )
    mhs1 = buat_orang_akun(db, "Mhs Prodi1", "m1@k.ac.id", nim="3001")
    mhs2 = buat_orang_akun(db, "Mhs Prodi2", "m2@k.ac.id", nim="3002")
    client.post(
        "/keanggotaan",
        json={"orang_id": str(mhs1.id), "prodi_id": kampus["prodi1"]["id"], "angkatan": 2024},
        headers=admin,
    )
    client.post(
        "/keanggotaan",
        json={"orang_id": str(mhs2.id), "prodi_id": kampus["prodi2"]["id"], "angkatan": 2024},
        headers=admin,
    )

    h = masuk(client, "kaprodi@k.ac.id")
    r = client.get("/ringkasan", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["struktur"]["prodi"] == 1
    assert data["mahasiswa_aktif"] == 1
    assert all(p["id"] == kampus["prodi1"]["id"] for p in data["mahasiswa_per_prodi"])
