"""Pemeriksaan versi token (tv) di verifier: akun ditangguhkan atau ganti sandi mematikan token."""

import os
import sys
import time
import uuid

import httpx
import jwt
import pytest

SECRET = "v" * 48
os.environ.update(JWT_SECRET=SECRET, IDENTITY_URL="http://identity.test", INTERNAL_TOKEN="rahasia-internal", TV_CACHE_TTL="5")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as verifier  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

klien = TestClient(verifier.app)
SUB = str(uuid.uuid4())
HDR = {"X-Original-Method": "GET", "X-Original-URI": "/api/identity/fakultas"}


def token(tv=1, roles=("mahasiswa",), **extra):
    payload = {"sub": SUB, "roles": list(roles), "exp": int(time.time()) + 600, **extra}
    if tv is not None:
        payload["tv"] = tv
    return jwt.encode(payload, SECRET, algorithm="HS256")


def verify(t):
    return klien.get("/verify", headers={**HDR, "Authorization": f"Bearer {t}"})


class IdentityPalsu:
    def __init__(self, respons):
        self.respons = respons
        self.panggilan = []

    def get(self, url, headers=None):
        self.panggilan.append((url, headers))
        if isinstance(self.respons, Exception):
            raise self.respons
        status, body = self.respons
        return httpx.Response(status, json=body, request=httpx.Request("GET", url))


@pytest.fixture(autouse=True)
def _bersih():
    verifier._tv_cache.clear()
    yield
    verifier._http = None


def pasang(monkeypatch, respons):
    palsu = IdentityPalsu(respons)
    monkeypatch.setattr(verifier, "_klien", lambda: palsu)
    return palsu


def test_versi_cocok_dan_akun_aktif_lolos(monkeypatch):
    palsu = pasang(monkeypatch, (200, {"versi_token": 1, "status": "aktif"}))
    r = verify(token(tv=1))
    assert r.status_code == 200
    url, headers = palsu.panggilan[0]
    assert url == f"http://identity.test/internal/akun/{SUB}/versi-token"
    assert headers["X-Internal-Token"] == "rahasia-internal"


def test_versi_token_sudah_naik_ditolak(monkeypatch):
    pasang(monkeypatch, (200, {"versi_token": 2, "status": "aktif"}))
    assert verify(token(tv=1)).status_code == 401


def test_akun_ditangguhkan_ditolak(monkeypatch):
    pasang(monkeypatch, (200, {"versi_token": 1, "status": "ditangguhkan"}))
    assert verify(token(tv=1)).status_code == 401


def test_akun_tidak_ada_ditolak(monkeypatch):
    pasang(monkeypatch, (404, {"detail": "x"}))
    assert verify(token(tv=1)).status_code == 401


def test_identity_mati_fail_closed_503(monkeypatch):
    pasang(monkeypatch, httpx.ConnectError("mati"))
    assert verify(token(tv=1)).status_code == 503


def test_respons_aneh_dari_identity_fail_closed(monkeypatch):
    pasang(monkeypatch, (500, {}))
    assert verify(token(tv=1)).status_code == 503


def test_token_lama_tanpa_tv_tidak_ditanyakan_ke_identity(monkeypatch):
    palsu = pasang(monkeypatch, (500, {}))
    assert verify(token(tv=None)).status_code == 200
    assert palsu.panggilan == []


def test_tv_bukan_angka_ditolak(monkeypatch):
    palsu = pasang(monkeypatch, (200, {"versi_token": 1, "status": "aktif"}))
    assert verify(token(tv="1")).status_code == 401
    assert verify(token(tv=True)).status_code == 401
    assert palsu.panggilan == []


def test_hasil_di_cache_singkat(monkeypatch):
    palsu = pasang(monkeypatch, (200, {"versi_token": 1, "status": "aktif"}))
    for _ in range(5):
        assert verify(token(tv=1)).status_code == 200
    assert len(palsu.panggilan) == 1


def test_cache_kedaluwarsa_memeriksa_ulang(monkeypatch):
    palsu = pasang(monkeypatch, (200, {"versi_token": 1, "status": "aktif"}))
    verify(token(tv=1))
    kunci = (SUB, 1)
    verifier._tv_cache[kunci] = (time.monotonic() - 1, True)
    verify(token(tv=1))
    assert len(palsu.panggilan) == 2


def test_penangguhan_terlihat_setelah_cache_habis(monkeypatch):
    pasang(monkeypatch, (200, {"versi_token": 1, "status": "aktif"}))
    assert verify(token(tv=1)).status_code == 200
    verifier._tv_cache.clear()  # meniru lewatnya TTL
    pasang(monkeypatch, (200, {"versi_token": 1, "status": "ditangguhkan"}))
    assert verify(token(tv=1)).status_code == 401
