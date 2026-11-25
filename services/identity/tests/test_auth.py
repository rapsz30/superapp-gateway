from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from src.core.config import get_settings
from src.core.security import buat_access_token
from src.models import Akun, RefreshToken
from tests.conftest import SANDI, buat_orang_akun, masuk


def _login(client, email="admin@kampus.ac.id", sandi=SANDI):
    return client.post("/auth/login", json={"email": email, "sandi": sandi})


def test_login_berhasil_dan_klaim_token(client, db, admin):
    r = _login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["peran"] == ["superadmin"]
    assert body["expires_in"] == 15 * 60
    s = get_settings()
    klaim = jwt.decode(body["access_token"], s.jwt_secret, algorithms=[s.jwt_algorithm], issuer=s.jwt_issuer)
    assert klaim["roles"] == ["superadmin"]
    assert klaim["scopes"] == [{"peran": "superadmin", "tipe": "global"}]
    assert {"sub", "orang", "tv", "exp", "iat", "iss"} <= set(klaim)


def test_email_tidak_peka_huruf(client, admin):
    assert _login(client, email="ADMIN@Kampus.Ac.Id").status_code == 200


def test_sandi_salah_dan_akun_tidak_ada_pesan_sama(client, admin):
    a = _login(client, sandi="salah-salah-salah")
    b = _login(client, email="tidak.ada@kampus.ac.id")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json() == {"detail": "Email atau sandi salah"}


def test_login_dibatasi_setelah_gagal_berulang(client, admin):
    for _ in range(5):
        assert _login(client, sandi="salah-salah-salah").status_code == 401
    assert _login(client, sandi="salah-salah-salah").status_code == 429
    # Sandi benar pun ditahan selama jendela pembatasan.
    assert _login(client).status_code == 429


def test_login_ditolak_bila_tanpa_peran_aktif(client, db):
    buat_orang_akun(db, "Tanpa Peran", "tp@kampus.ac.id")
    r = _login(client, email="tp@kampus.ac.id")
    assert r.status_code == 403
    assert "peran" in r.json()["detail"]


def test_akun_ditangguhkan_tidak_bisa_login(client, db, admin):
    buat_orang_akun(db, "X", "x@kampus.ac.id", peran="superadmin")
    akun = db.scalar(select(Akun).where(Akun.email == "x@kampus.ac.id"))
    akun.status = "ditangguhkan"
    db.commit()
    assert _login(client, email="x@kampus.ac.id").status_code == 401


def test_rute_terproteksi_tanpa_dan_dengan_token_rusak(client, admin):
    assert client.get("/auth/saya").status_code == 401
    assert client.get("/auth/saya", headers={"Authorization": "Bearer ngawur"}).status_code == 401
    assert client.get("/auth/saya", headers={"Authorization": "Basic abc"}).status_code == 401


def test_token_kedaluwarsa_ditolak(client, db, admin):
    akun = db.scalar(select(Akun))
    s = get_settings()
    lama = jwt.encode(
        {"sub": str(akun.id), "roles": ["superadmin"], "tv": 1, "iss": s.jwt_issuer,
         "exp": datetime.now(UTC) - timedelta(seconds=5)},
        s.jwt_secret, algorithm=s.jwt_algorithm,
    )
    r = client.get("/auth/saya", headers={"Authorization": f"Bearer {lama}"})
    assert r.status_code == 401


def test_token_tanda_tangan_salah_dan_alg_none_ditolak(client, db, admin):
    akun = db.scalar(select(Akun))
    s = get_settings()
    dasar = {"sub": str(akun.id), "roles": ["superadmin"], "tv": 1, "iss": s.jwt_issuer,
             "exp": datetime.now(UTC) + timedelta(minutes=5)}
    salah = jwt.encode(dasar, "y" * 48, algorithm="HS256")
    none_alg = jwt.encode(dasar, None, algorithm="none")
    for t in (salah, none_alg):
        assert client.get("/auth/saya", headers={"Authorization": f"Bearer {t}"}).status_code == 401


def test_klaim_peran_di_token_tidak_dipercaya(client, db):
    """Token membawa roles=superadmin, tetapi hak sebenarnya dari database."""
    from src.models import Orang

    orang = Orang(nama_lengkap="Biasa")
    db.add(orang)
    db.flush()
    akun = Akun(orang_id=orang.id, email="biasa@kampus.ac.id", sandi_hash="x", wajib_ganti_sandi=False)
    db.add(akun)
    db.commit()
    token, _ = buat_access_token(
        akun_id=akun.id, orang_id=orang.id, email=akun.email, peran=["superadmin"],
        scopes=[{"peran": "superadmin", "tipe": "global"}], versi_token=akun.versi_token,
        wajib_ganti_sandi=False,
    )
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/saya", headers=h).json()["peran"] == []
    assert client.post("/fakultas", json={"kode": "X", "nama": "X"}, headers=h).status_code == 403


def test_refresh_merotasi_token_dan_mendeteksi_pemakaian_ulang(client, admin):
    awal = _login(client).json()
    r1 = client.post("/auth/refresh", json={"refresh_token": awal["refresh_token"]})
    assert r1.status_code == 200
    baru = r1.json()
    assert baru["refresh_token"] != awal["refresh_token"]

    # Token lama dipakai lagi: ditolak dan semua sesi akun dicabut.
    ulang = client.post("/auth/refresh", json={"refresh_token": awal["refresh_token"]})
    assert ulang.status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": baru["refresh_token"]}).status_code == 401


def test_refresh_kedaluwarsa_ditolak(client, db, admin):
    awal = _login(client).json()
    for rt in db.scalars(select(RefreshToken)):  # fixture admin juga membuat satu token
        rt.kedaluwarsa = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert client.post("/auth/refresh", json={"refresh_token": awal["refresh_token"]}).status_code == 401


def test_logout_mencabut_refresh_token(client, admin):
    t = _login(client).json()
    h = {"Authorization": f"Bearer {t['access_token']}"}
    assert client.post("/auth/logout", json={"refresh_token": t["refresh_token"]}, headers=h).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_wajib_ganti_sandi_membatasi_akses(client, db):
    buat_orang_akun(db, "Baru", "baru@kampus.ac.id", peran="superadmin", wajib_ganti=True)
    t = _login(client, email="baru@kampus.ac.id").json()
    assert t["wajib_ganti_sandi"] is True
    h = {"Authorization": f"Bearer {t['access_token']}"}
    assert client.get("/fakultas", headers=h).status_code == 403
    assert client.get("/auth/saya", headers=h).status_code == 200

    # Kebijakan sandi
    assert client.post("/auth/ganti-sandi", headers=h, json={"sandi_lama": SANDI, "sandi_baru": "pendek"}).status_code == 400
    assert client.post("/auth/ganti-sandi", headers=h, json={"sandi_lama": "salah", "sandi_baru": "sandi-baru-9876"}).status_code == 400
    assert client.post("/auth/ganti-sandi", headers=h, json={"sandi_lama": SANDI, "sandi_baru": SANDI}).status_code == 400

    ok = client.post("/auth/ganti-sandi", headers=h, json={"sandi_lama": SANDI, "sandi_baru": "sandi-baru-9876"})
    assert ok.status_code == 200
    assert ok.json()["wajib_ganti_sandi"] is False
    # Token lama mati (versi_token naik); token baru bebas.
    assert client.get("/auth/saya", headers=h).status_code == 401
    h2 = {"Authorization": f"Bearer {ok.json()['access_token']}"}
    assert client.get("/fakultas", headers=h2).status_code == 200
    assert _login(client, email="baru@kampus.ac.id", sandi="sandi-baru-9876").status_code == 200
    assert _login(client, email="baru@kampus.ac.id").status_code == 401


def test_penangguhan_mematikan_token_yang_masih_berlaku(client, db, admin):
    buat_orang_akun(db, "Dua", "dua@kampus.ac.id", peran="superadmin")
    h_dua = masuk(client, "dua@kampus.ac.id")
    akun = db.scalar(select(Akun).where(Akun.email == "dua@kampus.ac.id"))
    r = client.patch(f"/akun/{akun.id}/status", json={"status": "ditangguhkan"}, headers=admin)
    assert r.status_code == 200
    assert client.get("/auth/saya", headers=h_dua).status_code == 401


def test_saya_menampilkan_pembimbing_dan_kaprodi_untuk_mahasiswa(client, admin, kampus, db):
    from tests.test_hak_akses import siapkan_dunia

    d = siapkan_dunia(client, db, admin, kampus)
    profil = client.get("/auth/saya", headers=d["h_mhs"]).json()
    assert profil["peran"] == ["mahasiswa"]
    assert profil["pembimbing_akademik"]["nama_lengkap"] == "Dosen PA"
    assert profil["kaprodi"]["nama_lengkap"] == "Kaprodi"
    assert profil["unit"][0]["nama"] == "Informatika"
    # Data akademik tersedia walau prodi belum punya panduan aktif (dipakai profil di frontend).
    ak = profil["akademik"]
    assert ak["prodi"]["nama"] == "Informatika" and ak["fakultas"]["nama"] == "Fakultas Teknologi Industri"
    assert ak["angkatan"] == 2020 and ak["status"] == "aktif"
    # Staf tidak punya blok akademik.
    assert client.get("/auth/saya", headers=d["h_kaprodi"]).json()["akademik"] is None


def test_jwt_secret_lemah_ditolak():
    from src.core.config import Settings

    for buruk in ("", "replace-with-secure-secret", "pendek"):
        with pytest.raises(ValueError):
            Settings(jwt_secret=buruk)
