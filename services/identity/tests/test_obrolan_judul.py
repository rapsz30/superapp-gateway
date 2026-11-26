"""Brainstorm judul: percakapan, kandidat, pembahasan, versi baru, dan kepemilikan."""

import pytest

from src.integrations import judul as layanan_judul
from src.integrations.judul import JudulGalat
from tests.test_hak_akses import siapkan_dunia


class JudulPalsu:
    def __init__(self):
        self.chat = []
        self.generate = []
        self.gagal = False

    def balas(self, pesan, prodi, mata_kuliah, tema, kandidat=None):
        if self.gagal:
            raise JudulGalat("mati")
        self.chat.append((pesan, kandidat))
        usulan = {"judul": "Versi lebih sempit", "tema": "ngawur", "deskripsi": "d", "metodologi": "m", "keywords": []}
        return {"balasan": f"balasan {len(self.chat)}", "saran": ["a", "b"], "usulan": usulan if kandidat else None}

    def rekomendasi(self, minat, prodi, mata_kuliah, tema, diskusi=""):
        if self.gagal:
            raise JudulGalat("mati")
        self.generate.append((minat, diskusi))
        n = len(self.generate)
        return [{"judul": f"Kandidat {n}.{i}", "tema": "keamanan siber", "deskripsi": "d", "metodologi": "m",
                 "keywords": ["k"], "referensi": [{"sitasi": "s", "link": "https://x"}]} for i in (1, 2, 3)]


@pytest.fixture
def dunia(client, db, admin, kampus, monkeypatch):
    d = siapkan_dunia(client, db, admin, kampus)
    d["layanan"] = JudulPalsu()
    monkeypatch.setattr(layanan_judul, "dapatkan_judul", lambda: d["layanan"])
    return d


def mulai(client, d):
    r = client.post("/judul/obrolan", json={"pesan": "tertarik keamanan jaringan"}, headers=d["h_mhs"])
    assert r.status_code == 201, r.text
    return r.json()


def test_brainstorm_dulu_baru_kandidat_tanpa_memilih(client, dunia):
    o = mulai(client, dunia)
    assert o["kandidat"] == [] and [p["peran"] for p in o["pesan"]] == ["mahasiswa", "asisten"]
    h, url = dunia["h_mhs"], f"/judul/obrolan/{o['id']}"
    o = client.post(f"{url}/kandidat", headers=h).json()
    assert len(o["kandidat"]) == 3 and not any(k["disimpan"] for k in o["kandidat"])
    assert o["kandidat"][0]["tema"] == "Keamanan Siber"
    assert "balasan 1" in dunia["layanan"].generate[0][1]
    assert client.get("/judul/saya", headers=h).json()["pengajuan"] is None
    daftar = client.get("/judul/obrolan", headers=h).json()["data"]
    assert daftar[0]["jumlah_kandidat"] == 3 and daftar[0]["jumlah_disimpan"] == 0


def test_bahas_kandidat_terpisah_lalu_simpan_versi(client, dunia):
    o = mulai(client, dunia)
    h, url = dunia["h_mhs"], f"/judul/obrolan/{o['id']}"
    kid = client.post(f"{url}/kandidat", headers=h).json()["kandidat"][0]["id"]
    o = client.post(f"{url}/pesan", json={"isi": "persempit", "kandidat_id": kid}, headers=h).json()
    pesan, kandidat = dunia["layanan"].chat[-1]
    assert kandidat["id"] == kid and [p["isi"] for p in pesan] == ["Latar minat saya: tertarik keamanan jaringan", "persempit"]
    jawab = o["pesan"][-1]
    assert jawab["kandidat_id"] == kid and jawab["usulan"]["tema"] == "Lainnya"
    # Brainstorm tidak tercampur pembahasan kandidat.
    client.post(f"{url}/pesan", json={"isi": "kembali"}, headers=h)
    assert "persempit" not in [p["isi"] for p in dunia["layanan"].chat[-1][0]]

    o = client.post(f"{url}/versi", json={"pesan_id": jawab["id"]}, headers=h).json()
    versi = o["kandidat"][-1]
    assert versi["versi_dari"] == kid and versi["disimpan"] and versi["referensi"] and len(o["kandidat"]) == 4
    assert client.post(f"{url}/versi", json={"pesan_id": jawab["id"]}, headers=h).status_code == 409
    o = client.patch(f"{url}/kandidat/{kid}", json={"disimpan": True}, headers=h).json()
    assert sum(k["disimpan"] for k in o["kandidat"]) == 2


def test_hanya_pemilik(client, dunia, admin):
    o = mulai(client, dunia)
    for h in (dunia["h_mhs2"], admin, dunia["h_dosen"]):
        assert client.get(f"/judul/obrolan/{o['id']}", headers=h).status_code in (403, 404)
    assert client.post("/judul/obrolan", json={"pesan": "halo"}, headers=dunia["h_dosen"]).status_code == 403
    assert client.get("/judul/obrolan", headers=dunia["h_mhs2"]).json()["data"] == []


def test_ai_gagal_tidak_menyimpan_apa_pun(client, dunia):
    h = dunia["h_mhs"]
    dunia["layanan"].gagal = True
    assert client.post("/judul/obrolan", json={"pesan": "halo dunia"}, headers=h).status_code == 502
    assert client.get("/judul/obrolan", headers=h).json()["data"] == []
    dunia["layanan"].gagal = False
    o = mulai(client, dunia)
    dunia["layanan"].gagal = True
    url = f"/judul/obrolan/{o['id']}"
    assert client.post(f"{url}/pesan", json={"isi": "lagi"}, headers=h).status_code == 502
    assert client.post(f"{url}/kandidat", headers=h).status_code == 502
    assert len(client.get(url, headers=h).json()["pesan"]) == 2


def test_batas_dan_riwayat_lama(client, dunia, monkeypatch):
    from src.api.routes import obrolan_judul as r

    h = dunia["h_mhs"]
    monkeypatch.setattr(r, "MAKS_KANDIDAT", 4)
    o = mulai(client, dunia)
    url = f"/judul/obrolan/{o['id']}"
    balasan = client.post(f"{url}/pesan", json={"isi": "lagi"}, headers=h)
    assert balasan.status_code == 200 and "sisa_pesan" not in balasan.json()
    awal = client.post(f"{url}/kandidat", headers=h).json()["kandidat"]
    client.patch(f"{url}/kandidat/{awal[0]['id']}", json={"disimpan": True}, headers=h)
    akhir = client.post(f"{url}/kandidat", headers=h).json()["kandidat"]
    assert len(akhir) == 4 and akhir[0]["id"] == awal[0]["id"]

    lama = client.post("/judul/rekomendasi", json={"minat": "data"}, headers=h).json()
    jumlah = len(dunia["layanan"].chat)
    baru = client.post("/judul/obrolan", json={"dari_rekomendasi": lama["id"]}, headers=h)
    assert baru.status_code == 201 and len(baru.json()["kandidat"]) == 3 and len(dunia["layanan"].chat) == jumlah
    assert client.post("/judul/obrolan", json={}, headers=h).status_code in (400, 422)
