from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from src.core.waktu import hari_ini
from tests.conftest import buat_orang_akun, masuk
from tests.test_hak_akses import siapkan_dunia


@pytest.fixture
def dunia(client, db, admin, kampus):
    return siapkan_dunia(client, db, admin, kampus)


def _pen(client, h, orang_id, peran, tipe, unit_id=None, **extra):
    return client.post(
        "/penugasan",
        json={"orang_id": str(orang_id), "peran": peran, "unit_tipe": tipe, "unit_id": unit_id, **extra},
        headers=h,
    )


# ---------------- Penugasan ----------------
def test_satu_kaprodi_aktif_lalu_pergantian(client, admin, kampus, db):
    p = kampus["prodi1"]["id"]
    a = buat_orang_akun(db, "A", "a@kampus.ac.id")
    b = buat_orang_akun(db, "B", "b@kampus.ac.id")
    r1 = _pen(client, admin, a.id, "kaprodi", "prodi", p)
    assert r1.status_code == 201
    r2 = _pen(client, admin, b.id, "kaprodi", "prodi", p)
    assert r2.status_code == 409 and "kaprodi aktif" in r2.json()["detail"]

    # Pergantian: akhiri yang lama, baru boleh.
    assert client.post(f"/penugasan/{r1.json()['id']}/akhiri", json={}, headers=admin).status_code == 200
    assert _pen(client, admin, b.id, "kaprodi", "prodi", p).status_code == 201
    # Riwayat tetap ada.
    semua = client.get("/penugasan", headers=admin, params={"unit_id": p, "peran": "kaprodi"}).json()
    assert semua["total"] == 2
    aktif = client.get("/penugasan", headers=admin, params={"unit_id": p, "peran": "kaprodi", "aktif": True}).json()
    assert aktif["total"] == 1


def test_admin_membuat_akun_dosen_langsung_di_prodi(client, admin, kampus):
    r = client.post(
        f"/prodi/{kampus['prodi1']['id']}/dosen",
        json={
            "nama_lengkap": "Dosen Baru",
            "nidn": "99887766",
            "email_kontak": "dosen.baru@kampus.ac.id",
            "email": "dosen.baru@kampus.ac.id",
            "sandi": "DosenBaru!123",
        },
        headers=admin,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["orang"]["nama_lengkap"] == "Dosen Baru"
    assert data["akun"]["email"] == "dosen.baru@kampus.ac.id"
    assert data["akun"]["sandi_sementara"] is None
    assert data["penugasan"]["peran"] == "dosen_pa"
    assert data["penugasan"]["unit_id"] == kampus["prodi1"]["id"]

    profil = client.get("/auth/saya", headers=masuk(client, "dosen.baru@kampus.ac.id", "DosenBaru!123")).json()
    assert profil["peran"] == ["dosen_pa"]
    assert profil["unit"][0]["id"] == kampus["prodi1"]["id"]


def test_pasangan_peran_unit_tidak_cocok_422(client, admin, kampus, db):
    a = buat_orang_akun(db, "A", "a@kampus.ac.id")
    r = _pen(client, admin, a.id, "kaprodi", "jurusan", kampus["jurusan"]["id"])
    assert r.status_code == 422
    r = _pen(client, admin, a.id, "superadmin", "prodi", kampus["prodi1"]["id"])
    assert r.status_code == 422
    r = _pen(client, admin, a.id, "dekan", "fakultas", None)
    assert r.status_code == 422


def test_unit_tidak_ada_atau_tidak_aktif_ditolak(client, admin, kampus, db):
    a = buat_orang_akun(db, "A", "a@kampus.ac.id")
    assert _pen(client, admin, a.id, "kaprodi", "prodi", str(uuid.uuid4())).status_code == 400
    client.patch(f"/prodi/{kampus['prodi2']['id']}", json={"aktif": False}, headers=admin)
    assert _pen(client, admin, a.id, "kaprodi", "prodi", kampus["prodi2"]["id"]).status_code == 400


def test_penugasan_masa_depan_belum_aktif_dan_tidak_masuk_token(client, admin, kampus, db):
    a = buat_orang_akun(db, "A", "a@kampus.ac.id", peran="dosen_pa", unit_tipe="prodi", unit_id=uuid.UUID(kampus["prodi1"]["id"]))
    besok = str(hari_ini() + timedelta(days=3))
    r = _pen(client, admin, a.id, "kaprodi", "prodi", kampus["prodi1"]["id"], mulai=besok)
    assert r.status_code == 201
    h = masuk(client, "a@kampus.ac.id")
    assert client.get("/auth/saya", headers=h).json()["peran"] == ["dosen_pa"]


def test_akhiri_dua_kali_dan_tanggal_salah(client, admin, kampus, db):
    a = buat_orang_akun(db, "A", "a@kampus.ac.id")
    pid = _pen(client, admin, a.id, "kaprodi", "prodi", kampus["prodi1"]["id"]).json()["id"]
    r = client.post(f"/penugasan/{pid}/akhiri", json={"selesai": "2000-01-01"}, headers=admin)
    assert r.status_code == 400
    assert client.post(f"/penugasan/{pid}/akhiri", json={}, headers=admin).status_code == 200
    assert client.post(f"/penugasan/{pid}/akhiri", json={}, headers=admin).status_code == 409


def test_superadmin_terakhir_tidak_boleh_diakhiri_atau_ditangguhkan(client, admin, db):
    from sqlalchemy import select

    from src.models import Akun, Penugasan

    pen = db.scalar(select(Penugasan).where(Penugasan.peran == "superadmin"))
    r = client.post(f"/penugasan/{pen.id}/akhiri", json={}, headers=admin)
    assert r.status_code == 409 and "terakhir" in r.json()["detail"]
    akun = db.scalar(select(Akun))
    r = client.patch(f"/akun/{akun.id}/status", json={"status": "nonaktif"}, headers=admin)
    assert r.status_code == 409

    # Dengan superadmin kedua, boleh.
    buat_orang_akun(db, "Dua", "dua@kampus.ac.id", peran="superadmin")
    assert client.post(f"/penugasan/{pen.id}/akhiri", json={}, headers=admin).status_code == 200


def test_kaprodi_hanya_mengatur_dosen_pa_di_prodinya(client, dunia, kampus, db):
    h = dunia["h_kaprodi"]
    calon = buat_orang_akun(db, "Calon PA", "calon@kampus.ac.id")
    ok = _pen(client, h, calon.id, "dosen_pa", "prodi", kampus["prodi1"]["id"])
    assert ok.status_code == 201
    assert _pen(client, h, calon.id, "dosen_pa", "prodi", kampus["prodi2"]["id"]).status_code == 403
    assert _pen(client, h, calon.id, "dosen_pa", "jurusan", kampus["jurusan"]["id"]).status_code == 403
    assert _pen(client, h, calon.id, "kaprodi", "prodi", kampus["prodi1"]["id"]).status_code == 403
    assert client.post(f"/penugasan/{ok.json()['id']}/akhiri", json={}, headers=h).status_code == 200


def test_pa_dengan_bimbingan_aktif_tidak_bisa_diakhiri(client, dunia, admin):
    dosen = dunia["orang"]["dosen"]
    pid = client.get("/penugasan", headers=admin, params={"orang_id": str(dosen.id)}).json()["data"][0]["id"]
    r = client.post(f"/penugasan/{pid}/akhiri", json={}, headers=admin)
    assert r.status_code == 409 and "Alihkan bimbingan" in r.json()["detail"]


# ---------------- Keanggotaan ----------------
def test_pindah_prodi_menutup_lama_membuka_baru_dan_mengakhiri_pa(client, dunia, admin, kampus):
    mhs = dunia["orang"]["mhs"]
    lama = client.get("/keanggotaan", headers=admin, params={"orang_id": str(mhs.id), "aktif": True}).json()["data"][0]
    r = client.post(f"/keanggotaan/{lama['id']}/pindah", json={"prodi_tujuan_id": kampus["prodi2"]["id"]}, headers=admin)
    assert r.status_code == 200
    assert r.json()["prodi_id"] == kampus["prodi2"]["id"] and r.json()["angkatan"] == 2020
    semua = client.get("/keanggotaan", headers=admin, params={"orang_id": str(mhs.id)}).json()["data"]
    assert sorted(x["status"] for x in semua) == ["aktif", "pindah"]
    assert client.get("/bimbingan", headers=admin, params={"mahasiswa_id": str(mhs.id), "aktif": True}).json()["total"] == 0
    # Hanya superadmin yang boleh pindah prodi.
    r = client.post(f"/keanggotaan/{r.json()['id']}/pindah", json={"prodi_tujuan_id": kampus["prodi1"]["id"]}, headers=dunia["h_kaprodi"])
    assert r.status_code == 403


def test_lulus_menutup_keanggotaan_dan_bimbingan(client, dunia, admin):
    mhs = dunia["orang"]["mhs"]
    k = client.get("/keanggotaan", headers=admin, params={"orang_id": str(mhs.id), "aktif": True}).json()["data"][0]
    r = client.post(f"/keanggotaan/{k['id']}/status", json={"status": "lulus"}, headers=dunia["h_kaprodi"])
    assert r.status_code == 200 and r.json()["selesai"] is not None
    assert client.get("/bimbingan", headers=admin, params={"mahasiswa_id": str(mhs.id), "aktif": True}).json()["total"] == 0
    # Setelah lulus tidak lagi punya peran mahasiswa, sehingga login ditolak (tanpa peran aktif).
    r = client.post("/auth/login", json={"email": "mhs@k.ac.id", "sandi": "sandi-uji-12345"})
    assert r.status_code == 403


def test_cuti_tetap_anggota_aktif(client, dunia, admin):
    mhs = dunia["orang"]["mhs"]
    k = client.get("/keanggotaan", headers=admin, params={"orang_id": str(mhs.id), "aktif": True}).json()["data"][0]
    r = client.post(f"/keanggotaan/{k['id']}/status", json={"status": "cuti"}, headers=admin)
    assert r.status_code == 200 and r.json()["selesai"] is None
    assert client.get("/auth/saya", headers=dunia["h_mhs"]).json()["peran"] == ["mahasiswa"]


def test_dua_keanggotaan_aktif_ditolak(client, dunia, admin, kampus):
    mhs = dunia["orang"]["mhs"]
    r = client.post("/keanggotaan", json={"orang_id": str(mhs.id), "prodi_id": kampus["prodi2"]["id"]}, headers=admin)
    assert r.status_code == 409


def test_kaprodi_tidak_bisa_mendaftarkan_ke_prodi_lain(client, dunia, db, kampus):
    o = buat_orang_akun(db, "Baru", "baru@kampus.ac.id")
    r = client.post("/keanggotaan", json={"orang_id": str(o.id), "prodi_id": kampus["prodi2"]["id"]}, headers=dunia["h_kaprodi"])
    assert r.status_code == 403
    r = client.post("/keanggotaan", json={"orang_id": str(o.id), "prodi_id": kampus["prodi1"]["id"]}, headers=dunia["h_kaprodi"])
    assert r.status_code == 201


# ---------------- Bimbingan ----------------
def test_bimbingan_butuh_pa_yang_mencakup_prodi(client, dunia, db, kampus):
    """mhs2 ada di prodi2; dosen PA hanya bertugas di prodi1."""
    admin_h = masuk(client, "admin@kampus.ac.id")
    r = client.post(
        "/bimbingan",
        json={"dosen_id": str(dunia["orang"]["dosen"].id), "mahasiswa_id": str(dunia["orang"]["mhs2"].id)},
        headers=admin_h,
    )
    assert r.status_code == 400 and "tidak memiliki penugasan dosen PA" in r.json()["detail"]

    # Penugasan PA tingkat jurusan mencakup semua prodi di jurusan itu.
    pa_jur = buat_orang_akun(db, "PA Jurusan", "pajur@kampus.ac.id")
    _pen(client, admin_h, pa_jur.id, "dosen_pa", "jurusan", kampus["jurusan"]["id"])
    r = client.post(
        "/bimbingan",
        json={"dosen_id": str(pa_jur.id), "mahasiswa_id": str(dunia["orang"]["mhs2"].id)},
        headers=admin_h,
    )
    assert r.status_code == 201


def test_mahasiswa_hanya_satu_pa_aktif(client, dunia, admin, db, kampus):
    pa2 = buat_orang_akun(db, "PA Dua", "pa2@kampus.ac.id")
    _pen(client, admin, pa2.id, "dosen_pa", "prodi", kampus["prodi1"]["id"])
    r = client.post("/bimbingan", json={"dosen_id": str(pa2.id), "mahasiswa_id": str(dunia["orang"]["mhs"].id)}, headers=admin)
    assert r.status_code == 409 and "dosen PA aktif" in r.json()["detail"]


def test_bimbingan_tanpa_keanggotaan_ditolak(client, admin, db, kampus):
    pa = buat_orang_akun(db, "PA", "pa@kampus.ac.id")
    non = buat_orang_akun(db, "Non", "non@kampus.ac.id")
    _pen(client, admin, pa.id, "dosen_pa", "prodi", kampus["prodi1"]["id"])
    r = client.post("/bimbingan", json={"dosen_id": str(pa.id), "mahasiswa_id": str(non.id)}, headers=admin)
    assert r.status_code == 400


def test_pindahkan_massal_lalu_pa_lama_bisa_diakhiri(client, dunia, admin, db, kampus):
    pa2 = buat_orang_akun(db, "PA Dua", "pa2@kampus.ac.id")
    _pen(client, admin, pa2.id, "dosen_pa", "prodi", kampus["prodi1"]["id"])
    dosen = dunia["orang"]["dosen"]
    r = client.post(
        "/bimbingan/pindahkan",
        json={"dosen_asal_id": str(dosen.id), "dosen_tujuan_id": str(pa2.id)},
        headers=dunia["h_kaprodi"],
    )
    assert r.status_code == 200 and r.json()["dialihkan"] == 1
    profil = client.get("/auth/saya", headers=dunia["h_mhs"]).json()
    assert profil["pembimbing_akademik"]["nama_lengkap"] == "PA Dua"
    # Riwayat bimbingan lama tetap ada (tertutup).
    riwayat = client.get("/bimbingan", headers=admin, params={"mahasiswa_id": str(dunia["orang"]["mhs"].id)}).json()
    assert riwayat["total"] == 2
    # Sekarang PA lama tidak punya bimbingan aktif: penugasannya boleh diakhiri.
    pid = client.get("/penugasan", headers=admin, params={"orang_id": str(dosen.id)}).json()["data"][0]["id"]
    assert client.post(f"/penugasan/{pid}/akhiri", json={}, headers=admin).status_code == 200


def test_pindahkan_ke_dosen_yang_tidak_mencakup_prodi_ditolak_dan_atomik(client, dunia, admin, db):
    luar = buat_orang_akun(db, "Bukan PA", "bukan@kampus.ac.id")
    r = client.post(
        "/bimbingan/pindahkan",
        json={"dosen_asal_id": str(dunia["orang"]["dosen"].id), "dosen_tujuan_id": str(luar.id)},
        headers=admin,
    )
    assert r.status_code == 400
    # Tidak ada yang berubah.
    assert client.get("/bimbingan", headers=admin, params={"aktif": True}).json()["total"] == 1


def test_kaprodi_tidak_boleh_memindahkan_mahasiswa_prodi_lain(client, dunia, admin, db, kampus):
    # PA yang membimbing mahasiswa prodi2: kaprodi prodi1 tidak berwenang.
    pa_jur = buat_orang_akun(db, "PA Jur", "pajur@kampus.ac.id")
    pa_lain = buat_orang_akun(db, "PA Lain", "palain@kampus.ac.id")
    for o in (pa_jur, pa_lain):
        _pen(client, admin, o.id, "dosen_pa", "jurusan", kampus["jurusan"]["id"])
    client.post("/bimbingan", json={"dosen_id": str(pa_jur.id), "mahasiswa_id": str(dunia["orang"]["mhs2"].id)}, headers=admin)
    r = client.post(
        "/bimbingan/pindahkan",
        json={"dosen_asal_id": str(pa_jur.id), "dosen_tujuan_id": str(pa_lain.id)},
        headers=dunia["h_kaprodi"],
    )
    assert r.status_code == 403
