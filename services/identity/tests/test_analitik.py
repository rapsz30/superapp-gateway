"""Dashboard kaprodi dari API laporan AlurKerja (ditiru)."""

import httpx
import pytest

from src.core.config import get_settings
from src.integrations import laporan
from tests.test_hak_akses import siapkan_dunia


class Laporan:
    def __init__(self):
        self.permintaan = []
        self.gagal_kartu = False
        self.gagal_dashboard = False
        self.token_ditolak_sekali = False

    def handler(self, r: httpx.Request) -> httpx.Response:
        jalur = r.url.path
        self.permintaan.append(jalur)
        if jalur.endswith("/login"):
            return httpx.Response(200, json={"data": {"access_token": "tkn", "expires_in": 3600}})
        assert r.headers["authorization"] == "Bearer tkn" and r.headers["x-act-env"] == "LIVE"
        if self.token_ditolak_sekali:
            self.token_ditolak_sekali = False
            return httpx.Response(401)
        if jalur == "/api/v1/report/1/dashboard/3/app":
            return httpx.Response(200, json={"name": "Judul", "dashboard_items": [], "questions": []})
        if jalur == "/api/v1/report/1/dashboard/2/app":
            if self.gagal_dashboard:
                return httpx.Response(500)
            return httpx.Response(200, json={
                "name": "Dashboard Kaprodi", "description": "rekap",
                "dashboard_items": [
                    {"i": "b", "question_id": 10, "x": 6, "y": 0, "w": 6, "h": 4},
                    {"i": "a", "question_id": 9, "x": 0, "y": 0, "w": 6, "h": 4},
                    {"i": "h", "type": "header", "x": 0, "y": 8, "w": 12, "h": 1},
                ],
                "questions": [
                    {"id": 9, "title": "Total", "visualization_type": "number", "query": "SELECT rahasia",
                     "chart_config": {"value_column": "n", "header": "Total", "lain": 1}},
                    {"id": 10, "title": "Per prodi", "visualization_type": "table", "query": "SELECT 2",
                     "chart_config": {}},
                ],
            })
        if jalur.endswith("/question/10/execute-query") and self.gagal_kartu:
            return httpx.Response(500)
        return httpx.Response(200, json={"success": True, "data": {"results": [{"n": 2}]}})


@pytest.fixture
def tiruan(monkeypatch):
    t = Laporan()
    laporan._token.clear()
    klien = laporan.LaporanKlien(
        "https://alurkerja.test/engine-rest", "slug", "id", "kunci", tenant="1", workspace="w", env="LIVE",
        http=httpx.Client(transport=httpx.MockTransport(t.handler)),
    )
    monkeypatch.setattr(laporan, "dapatkan_laporan", lambda: klien)
    for tab, nomor in (("ringkasan", "2"), ("matkul", ""), ("judul", "3")):
        monkeypatch.setattr(get_settings(), f"alurkerja_dashboard_{tab}", nomor)
    return t


@pytest.fixture
def dunia(client, db, admin, kampus):
    return siapkan_dunia(client, db, admin, kampus)


def ambil(client, h):
    return client.get("/analitik/dashboard", headers=h)


def test_kaprodi_melihat_susunan_dan_angka_tanpa_sql(client, dunia, tiruan):
    r = ambil(client, dunia["h_kaprodi"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["judul"] == "Dashboard Kaprodi"
    assert [k["id"] for k in d["kartu"]] == ["a", "b", "h"]
    assert d["kartu"][0]["baris"] == [{"n": 2}]
    assert d["kartu"][0]["konfigurasi"] == {"value_column": "n", "header": "Total"}
    assert d["kartu"][2]["galat"]
    assert "SELECT" not in r.text and "rahasia" not in r.text


def test_hanya_kaprodi_dan_superadmin(client, dunia, admin, tiruan):
    assert ambil(client, admin).status_code == 200
    for peran in ("h_mhs", "h_dosen"):
        assert ambil(client, dunia[peran]).status_code == 403
    assert client.get("/analitik/dashboard").status_code == 401


def test_satu_kartu_gagal_tidak_menggagalkan_dashboard(client, dunia, tiruan):
    tiruan.gagal_kartu = True
    kartu = ambil(client, dunia["h_kaprodi"]).json()["kartu"]
    assert kartu[0]["galat"] is None and kartu[1]["galat"] and kartu[1]["baris"] == []


def test_token_ditolak_masuk_ulang_dan_galat_dashboard(client, dunia, tiruan):
    tiruan.token_ditolak_sekali = True
    assert ambil(client, dunia["h_kaprodi"]).status_code == 200
    assert sum(p.endswith("/login") for p in tiruan.permintaan) == 2
    tiruan.gagal_dashboard = True
    assert ambil(client, dunia["h_kaprodi"]).status_code == 502


def test_tanpa_konfigurasi(client, dunia):
    assert ambil(client, dunia["h_kaprodi"]).status_code == 503


def test_tiap_tab_membaca_dashboardnya_sendiri(client, dunia, tiruan):
    h = dunia["h_kaprodi"]
    assert client.get("/analitik/dashboard?tab=judul", headers=h).json()["judul"] == "Judul"
    assert client.get("/analitik/dashboard?tab=matkul", headers=h).status_code == 503
    assert client.get("/analitik/dashboard?tab=lain", headers=h).status_code == 422
    assert client.get("/analitik/dashboard?tab=judul", headers=dunia["h_dosen"]).status_code == 403
