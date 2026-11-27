"""Registrasi publik, mahasiswa dummy, dan panduan pribadi."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from src.core.config import get_settings
from src.models import Akun, Bimbingan, KeanggotaanProdi, Orang, PanduanAkademik, Penugasan
from tests.conftest import PDF_PANDUAN, SANDI, buat_orang_akun, masuk


@pytest.fixture
def dummy(client, db, admin, monkeypatch):
    """Prodi DUMMY/UMUM/UMUM + dosen PA/kaprodi, sakelar registrasi aktif."""
    f = client.post("/fakultas", json={"kode": "DUMMY", "nama": "Fakultas Dummy"}, headers=admin).json()
    j = client.post(
        "/jurusan", json={"fakultas_id": f["id"], "kode": "UMUM", "nama": "Umum"}, headers=admin
    ).json()
    p = client.post(
        "/prodi",
        json={"jurusan_id": j["id"], "kode": "UMUM", "nama": "Program Umum", "jenjang": "S1"},
        headers=admin,
    ).json()
    dosen = buat_orang_akun(db, "Dosen Dummy", "dosen.dummy@kampus.ac.id", nidn="9900000001")
    for peran in ("kaprodi", "dosen_pa"):
        db.add(
            Penugasan(
                orang_id=dosen.id,
                peran=peran,
                unit_tipe="prodi",
                unit_id=p["id"],
                mulai=date(2020, 1, 1),
            )
        )
    db.commit()
    s = get_settings()
    monkeypatch.setattr(s, "registrasi_aktif", True)
    monkeypatch.setattr(s, "prodi_terbuka", "DUMMY/UMUM/UMUM")
    monkeypatch.setattr(s, "registrasi_maks_per_jam", 100)
    monkeypatch.setattr(s, "dummy_maks_sekali", 50)
    return {"prodi": p, "dosen": dosen, "admin": admin}


def test_status_registrasi(client, dummy):
    r = client.get("/auth/registrasi")
    assert r.status_code == 200
    assert r.json() == {"aktif": True}


def test_registrasi_mati_404(client, dummy, monkeypatch):
    monkeypatch.setattr(get_settings(), "registrasi_aktif", False)
    assert client.get("/auth/registrasi").json()["aktif"] is False
    r = client.post(
        "/auth/register",
        json={
            "nama_lengkap": "A",
            "email": "a@contoh.ac.id",
            "sandi": SANDI,
            "program_studi": "IF",
            "perguruan_tinggi": "UII",
        },
    )
    assert r.status_code == 404


def test_registrasi_sukses(client, db, dummy):
    r = client.post(
        "/auth/register",
        json={
            "nama_lengkap": "Pendaftar Satu",
            "email": "pendaftar1@contoh.ac.id",
            "sandi": SANDI,
            "program_studi": "Teknik Informatika",
            "perguruan_tinggi": "Universitas Contoh",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["wajib_ganti_sandi"] is False
    assert "mahasiswa" in body["peran"]

    akun = db.scalar(select(Akun).where(Akun.email == "pendaftar1@contoh.ac.id"))
    assert akun is not None
    orang = db.get(Orang, akun.orang_id)
    assert orang.prodi_isian == "Teknik Informatika"
    assert orang.pt_isian == "Universitas Contoh"
    assert orang.nim and orang.nim.startswith("98")
    assert db.scalar(
        select(KeanggotaanProdi).where(
            KeanggotaanProdi.orang_id == orang.id, KeanggotaanProdi.selesai.is_(None)
        )
    )
    assert db.scalar(
        select(Bimbingan).where(Bimbingan.mahasiswa_id == orang.id, Bimbingan.selesai.is_(None))
    )

    h = {"Authorization": f"Bearer {body['access_token']}"}
    saya = client.get("/auth/saya", headers=h).json()
    assert saya["panduan_pribadi"] is True
    assert saya["prodi_isian"] == "Teknik Informatika"


def test_registrasi_email_bentrok_dan_cadangan(client, dummy):
    payload = {
        "nama_lengkap": "X",
        "email": "sama@contoh.ac.id",
        "sandi": SANDI,
        "program_studi": "IF",
        "perguruan_tinggi": "UII",
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409
    payload["email"] = "mahasiswa12@x.ac.id"
    assert client.post("/auth/register", json=payload).status_code == 409


def test_registrasi_field_tambahan_ditolak(client, dummy):
    r = client.post(
        "/auth/register",
        json={
            "nama_lengkap": "X",
            "email": "extra@contoh.ac.id",
            "sandi": SANDI,
            "program_studi": "IF",
            "perguruan_tinggi": "UII",
            "peran": ["superadmin"],
        },
    )
    assert r.status_code == 422


def test_registrasi_dosen_belum_siap_503(client, db, dummy, monkeypatch):
    # Akhiri penugasan kaprodi.
    for p in db.scalars(select(Penugasan).where(Penugasan.peran == "kaprodi")).all():
        p.selesai = date(2020, 1, 2)
    db.commit()
    r = client.post(
        "/auth/register",
        json={
            "nama_lengkap": "Y",
            "email": "y@contoh.ac.id",
            "sandi": SANDI,
            "program_studi": "IF",
            "perguruan_tinggi": "UII",
        },
    )
    assert r.status_code == 503


def test_registrasi_batas_per_jam(client, dummy, monkeypatch):
    monkeypatch.setattr(get_settings(), "registrasi_maks_per_jam", 1)
    ok = {
        "nama_lengkap": "A",
        "email": "batas1@contoh.ac.id",
        "sandi": SANDI,
        "program_studi": "IF",
        "perguruan_tinggi": "UII",
    }
    assert client.post("/auth/register", json=ok).status_code == 201
    ok["email"] = "batas2@contoh.ac.id"
    assert client.post("/auth/register", json=ok).status_code == 429


def test_mahasiswa_dummy_batch(client, db, dummy):
    pid = dummy["prodi"]["id"]
    r = client.post(
        f"/prodi/{pid}/mahasiswa-dummy",
        json={"jumlah": 3, "sandi": SANDI},
        headers=dummy["admin"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dibuat"] == 3
    assert [a["email"] for a in body["akun"]] == [
        "mahasiswa1@studentgateway.id",
        "mahasiswa2@studentgateway.id",
        "mahasiswa3@studentgateway.id",
    ]
    assert "sandi" not in body and all("sandi" not in a for a in body["akun"])

    r2 = client.post(
        f"/prodi/{pid}/mahasiswa-dummy",
        json={"jumlah": 2, "sandi": SANDI},
        headers=dummy["admin"],
    )
    assert r2.json()["akun"][0]["email"] == "mahasiswa4@studentgateway.id"
    assert client.post("/auth/login", json={"email": "mahasiswa1@studentgateway.id", "sandi": SANDI}).status_code == 200


def test_mahasiswa_dummy_hanya_superadmin_dan_prodi_terbuka(client, db, admin, kampus, dummy):
    # Bukan superadmin
    buat_orang_akun(
        db, "Kap", "kap@kampus.ac.id", peran="kaprodi", unit_tipe="prodi", unit_id=kampus["prodi1"]["id"]
    )
    h = masuk(client, "kap@kampus.ac.id")
    assert (
        client.post(
            f"/prodi/{dummy['prodi']['id']}/mahasiswa-dummy",
            json={"jumlah": 1, "sandi": SANDI},
            headers=h,
        ).status_code
        == 403
    )
    # Prodi bukan dummy
    assert (
        client.post(
            f"/prodi/{kampus['prodi1']['id']}/mahasiswa-dummy",
            json={"jumlah": 1, "sandi": SANDI},
            headers=admin,
        ).status_code
        == 400
    )


def test_panduan_pribadi_isolasi(client, db, dummy):
    def daftar(email: str) -> dict:
        r = client.post(
            "/auth/register",
            json={
                "nama_lengkap": email.split("@")[0],
                "email": email,
                "sandi": SANDI,
                "program_studi": "IF",
                "perguruan_tinggi": "UII",
            },
        )
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    h1 = daftar("mhs1@contoh.ac.id")
    h2 = daftar("mhs2@contoh.ac.id")

    u1 = client.post(
        "/panduan/saya",
        headers=h1,
        data={"judul": "Panduan saya"},
        files={"berkas": ("p.pdf", PDF_PANDUAN, "application/pdf")},
    )
    assert u1.status_code == 201, u1.text
    gid1 = u1.json()["id"]
    assert u1.json()["versi"] == 1

    u2 = client.post(
        "/panduan/saya",
        headers=h2,
        data={"judul": "Panduan dua"},
        files={"berkas": ("p.pdf", PDF_PANDUAN, "application/pdf")},
    )
    assert u2.status_code == 201
    assert u2.json()["versi"] == 1
    assert u2.json()["id"] != gid1

    # Mahasiswa lain tidak boleh unduh
    assert client.get(f"/panduan/{gid1}/berkas", headers=h2).status_code == 404
    assert client.get(f"/panduan/{gid1}/berkas", headers=h1).status_code == 200

    # DPA boleh
    h_dosen = masuk(client, "dosen.dummy@kampus.ac.id")
    assert client.get(f"/panduan/{gid1}/berkas", headers=h_dosen).status_code == 200

    # Konteks memakai panduan pemilik
    k1 = client.get("/akademik/konteks?tanpa_teks=true", headers=h1).json()
    assert k1["panduan"]["id"] == gid1
    assert k1["panduan_pribadi"] is True

    # Unggah baru mengarsipkan lama
    u1b = client.post(
        "/panduan/saya",
        headers=h1,
        data={"judul": "Versi 2"},
        files={"berkas": ("p2.pdf", PDF_PANDUAN, "application/pdf")},
    )
    assert u1b.status_code == 201
    assert u1b.json()["versi"] == 2
    lama = db.get(PanduanAkademik, gid1)
    assert lama.status == "diarsipkan"


def test_unggah_panduan_prodi_dummy_ditolak(client, dummy):
    r = client.post(
        f"/prodi/{dummy['prodi']['id']}/panduan",
        headers=dummy["admin"],
        data={"judul": "Tidak boleh"},
        files={"berkas": ("p.pdf", PDF_PANDUAN, "application/pdf")},
    )
    assert r.status_code == 409


def test_prodi_terbuka_flag(client, dummy):
    r = client.get(f"/prodi/{dummy['prodi']['id']}", headers=dummy["admin"])
    assert r.status_code == 200
    assert r.json()["terbuka"] is True
