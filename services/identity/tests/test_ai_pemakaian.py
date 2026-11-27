"""Pencatatan dan ringkasan pemakaian AI."""

from __future__ import annotations

import pytest

from sqlalchemy import select

from src.core.config import get_settings
from src.models import Akun
from tests.conftest import buat_orang_akun, masuk

TOKEN = "a" * 40
CATATAN = {
    "layanan": "judul",
    "fitur": "obrolan_judul",
    "model": "gpt-6-luna",
    "token_masuk": 1000,
    "token_keluar": 200,
    "durasi_ms": 900,
}


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "ai_catat_token", TOKEN)
    monkeypatch.setattr(s, "ai_harga_masuk_per_juta", "")
    monkeypatch.setattr(s, "ai_harga_keluar_per_juta", "")


def _catat(client, token=TOKEN, **ubah):
    return client.post("/internal/ai-pemakaian", json={**CATATAN, **ubah}, headers={"X-AI-Token": token})


def test_catat_butuh_token(client, monkeypatch):
    assert _catat(client, token="salah").status_code == 404
    assert client.post("/internal/ai-pemakaian", json=CATATAN).status_code == 404
    monkeypatch.setattr(get_settings(), "ai_catat_token", "")
    assert _catat(client, token="").status_code == 404


def test_isian_tidak_sah_ditolak(client):
    assert _catat(client, layanan="lain").status_code == 422
    assert _catat(client, token_masuk=-1).status_code == 422


def test_ringkasan_hanya_superadmin(client, db):
    buat_orang_akun(db, "Kaprodi", "kp@uji.ac.id", peran="dosen_pa")
    assert client.get("/ai-pemakaian", headers=masuk(client, "kp@uji.ac.id")).status_code == 403
    assert client.get("/ai-pemakaian").status_code == 401


def test_ringkasan_menjumlahkan(client, db, monkeypatch):
    buat_orang_akun(db, "Admin", "admin@uji.ac.id", peran="superadmin")
    mhs = buat_orang_akun(db, "Mahasiswa", "mhs@uji.ac.id")
    akun_id = str(db.scalar(select(Akun.id).where(Akun.orang_id == mhs.id)))
    assert _catat(client, akun_id=akun_id).status_code == 204
    assert _catat(client, akun_id=akun_id, berhasil=False, token_masuk=0, token_keluar=0).status_code == 204
    assert _catat(client, layanan="matkul", fitur="baca_khs").status_code == 204
    h = masuk(client, "admin@uji.ac.id")

    r = client.get("/ai-pemakaian", headers=h).json()
    assert r["total"] == {"panggilan": 3, "gagal": 1, "token_masuk": 2000, "token_keluar": 400, "biaya_usd": None}
    assert len(r["per_hari"]) == 30 and r["per_hari"][-1]["panggilan"] == 3
    assert {(f["layanan"], f["panggilan"]) for f in r["per_fitur"]} == {("judul", 2), ("matkul", 1)}
    pengguna = {p["email"]: p["panggilan"] for p in r["per_pengguna"]}
    assert pengguna == {"mhs@uji.ac.id": 2, None: 1}

    s = get_settings()
    monkeypatch.setattr(s, "ai_harga_masuk_per_juta", "1")
    monkeypatch.setattr(s, "ai_harga_keluar_per_juta", "10")
    assert client.get("/ai-pemakaian", headers=h).json()["total"]["biaya_usd"] == 0.006

    lama = client.get("/ai-pemakaian?dari=2020-01-01&sampai=2020-01-31", headers=h).json()
    assert lama["total"]["panggilan"] == 0 and lama["per_pengguna"] == []
    assert client.get("/ai-pemakaian?dari=2026-02-01&sampai=2026-01-01", headers=h).status_code == 400
