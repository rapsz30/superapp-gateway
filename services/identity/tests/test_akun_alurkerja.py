"""Sinkron akun dosen ke AlurKerja (Keycloak, API admin, dan engine ditiru)."""

import json

import httpx
import pytest

from src.domain import akun_alurkerja
from src.integrations import alurkerja, alurkerja_admin
from src.integrations.alurkerja import AlurKerjaKlien
from src.integrations.alurkerja_admin import AdminKlien
from tests.test_hak_akses import siapkan_dunia


class Tiruan:
    def __init__(self):
        self.ada = {"kaprodi@k.ac.id"}
        self.dibuat = []
        self.konflik = set()
        self.tolak_masuk = False
        self.token_basi_sekali = False
        self.masuk = 0

    def handler(self, r: httpx.Request) -> httpx.Response:
        jalur = r.url.path
        if jalur == "/engine-rest/user":
            email = r.url.params["id"]
            return httpx.Response(200, json=[{"id": email}] if email in self.ada else [])
        if jalur == "/sso/realms/alurkerja/protocol/openid-connect/token":
            self.masuk += 1
            if self.tolak_masuk:
                return httpx.Response(401, json={})
            assert b"grant_type=client_credentials" in r.content
            return httpx.Response(200, json={"access_token": "tkn"})
        assert jalur == "/api/v1/tenant/admin/users" and r.headers["authorization"] == "Bearer tkn"
        if self.token_basi_sekali:
            self.token_basi_sekali = False
            return httpx.Response(401)
        isi = json.loads(r.content)
        if isi["email"] in self.konflik:
            return httpx.Response(409, json={"message": "sudah ada"})
        self.dibuat.append(isi)
        return httpx.Response(201, json={"id": "u1", "password_email_sent": True})


@pytest.fixture
def tiruan(monkeypatch):
    t = Tiruan()
    http = httpx.Client(transport=httpx.MockTransport(t.handler))
    admin = AdminKlien("https://alurkerja.test/engine-rest", "alurkerja", "sync", "rahasia", "1", http=http)
    engine = AlurKerjaKlien("https://alurkerja.test", "svc", "p", "x", http=http)
    monkeypatch.setattr(alurkerja_admin, "dapatkan_admin", lambda: admin)
    monkeypatch.setattr(alurkerja, "dapatkan_klien", lambda *a: engine)
    akun_alurkerja._selesai.clear()
    return t


@pytest.fixture
def dunia(client, db, admin, kampus):
    return siapkan_dunia(client, db, admin, kampus)


def test_coba_tidak_membuat_apa_pun(db, dunia, tiruan):
    hasil = akun_alurkerja.sinkron(db, coba=True)
    assert "dosen@k.ac.id" in hasil["akan_dibuat"] and "kaprodi@k.ac.id" not in hasil["akan_dibuat"]
    assert tiruan.dibuat == [] and tiruan.masuk == 0


def test_hanya_dosen_yang_belum_terdaftar_dan_sekali_saja(db, dunia, tiruan):
    hasil = akun_alurkerja.sinkron(db)
    email = [x["email"] for x in tiruan.dibuat]
    assert email == hasil["dibuat"] and "dosen@k.ac.id" in email
    assert "kaprodi@k.ac.id" not in email and not any(e.startswith(("mhs", "dekan", "kajur", "asing@")) for e in email)
    assert tiruan.dibuat[0]["role"] == "member" and tiruan.dibuat[0]["workspace_id"] == 1
    jumlah = len(tiruan.dibuat)
    assert akun_alurkerja.sinkron(db)["dibuat"] == [] and len(tiruan.dibuat) == jumlah


def test_konflik_token_basi_dan_gagal_masuk(db, dunia, tiruan):
    tiruan.tolak_masuk = True
    assert "dosen@k.ac.id" in akun_alurkerja.sinkron(db)["gagal"] and tiruan.dibuat == []
    tiruan.tolak_masuk = False
    tiruan.token_basi_sekali = True
    tiruan.konflik.add("dosen@k.ac.id")
    hasil = akun_alurkerja.sinkron(db)  # kegagalan sebelumnya dicoba lagi
    assert hasil["perlu_manual"] == ["dosen@k.ac.id"] and hasil["gagal"] == []


def test_nonaktif_tanpa_konfigurasi(db, dunia):
    assert akun_alurkerja.mulai_latar() is None
    assert akun_alurkerja.sinkron(db) == {"dibuat": [], "perlu_manual": [], "akan_dibuat": [], "gagal": []}
