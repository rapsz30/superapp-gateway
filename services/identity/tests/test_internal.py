"""Endpoint internal untuk verifier gateway."""

from __future__ import annotations

from sqlalchemy import select

from src.models import Akun
from tests.conftest import INTERNAL_TOKEN, SANDI


def _akun_id(db, email="admin@kampus.ac.id"):
    return db.scalar(select(Akun.id).where(Akun.email == email))


def test_tanpa_atau_dengan_token_salah_dianggap_tidak_ada(client, db, admin):
    aid = _akun_id(db)
    assert client.get(f"/internal/akun/{aid}/versi-token").status_code == 404
    assert client.get(f"/internal/akun/{aid}/versi-token", headers={"X-Internal-Token": "salah"}).status_code == 404


def test_mengembalikan_versi_dan_status(client, db, admin):
    aid = _akun_id(db)
    r = client.get(f"/internal/akun/{aid}/versi-token", headers={"X-Internal-Token": INTERNAL_TOKEN})
    assert r.status_code == 200
    assert r.json() == {"versi_token": 1, "status": "aktif"}
    assert "sandi" not in r.text


def test_versi_naik_setelah_ganti_sandi(client, db, admin):
    aid = _akun_id(db)
    t = client.post("/auth/login", json={"email": "admin@kampus.ac.id", "sandi": SANDI}).json()
    h = {"Authorization": f"Bearer {t['access_token']}"}
    client.post("/auth/ganti-sandi", headers=h, json={"sandi_lama": SANDI, "sandi_baru": "Sandi-Baru-12345"})
    r = client.get(f"/internal/akun/{aid}/versi-token", headers={"X-Internal-Token": INTERNAL_TOKEN})
    assert r.json()["versi_token"] == 2


def test_akun_tidak_ada_404(client):
    r = client.get(
        "/internal/akun/00000000-0000-0000-0000-000000000000/versi-token",
        headers={"X-Internal-Token": INTERNAL_TOKEN},
    )
    assert r.status_code == 404


def test_tidak_muncul_di_dokumentasi_api(client):
    assert "/internal" not in client.get("/openapi.json").text
