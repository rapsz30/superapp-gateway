"""Konteks akademik: dasar rekomendasi matkul = panduan aktif prodi mahasiswa itu sendiri."""

from __future__ import annotations

import io

import pytest

from tests.conftest import TEKS_PANDUAN, buat_pdf
from tests.test_hak_akses import siapkan_dunia


@pytest.fixture
def dunia(client, db, admin, kampus):
    return siapkan_dunia(client, db, admin, kampus)


def _siapkan_panduan(client, h, prodi_id, judul, baris, aktifkan=True):
    r = client.post(
        f"/prodi/{prodi_id}/panduan",
        data={"judul": judul},
        files={"berkas": ("p.pdf", io.BytesIO(buat_pdf(baris)), "application/pdf")},
        headers=h,
    )
    assert r.status_code == 201, r.text
    if aktifkan:
        assert client.post(f"/panduan/{r.json()['id']}/aktifkan", headers=h).status_code == 200
    return r.json()


def test_teks_disimpan_saat_unggah(client, dunia, kampus):
    g = _siapkan_panduan(client, dunia["h_kaprodi"], kampus["prodi1"]["id"], "P1", TEKS_PANDUAN, aktifkan=False)
    assert g["teks_karakter"] and g["teks_karakter"] > 200


def test_mahasiswa_mendapat_panduan_prodinya_sendiri(client, dunia, kampus):
    """mhs di prodi1 dan mhs2 di prodi2: masing-masing hanya menerima panduan prodinya."""
    _siapkan_panduan(client, dunia["h_kaprodi"], kampus["prodi1"]["id"], "Panduan IF", TEKS_PANDUAN)
    # prodi2 belum punya panduan aktif.
    k2 = client.get("/akademik/konteks", headers=dunia["h_mhs2"])
    assert k2.status_code == 404 and "belum memiliki panduan akademik aktif" in k2.json()["detail"]

    k1 = client.get("/akademik/konteks", headers=dunia["h_mhs"]).json()
    assert k1["prodi"]["kode"] == "IF-S1"
    assert k1["prodi"]["jurusan"]["kode"] == "IF" and k1["prodi"]["fakultas"]["kode"] == "FTI"
    assert k1["mahasiswa"]["nim"] == "20110001"
    assert k1["panduan"]["versi"] == 1 and "Struktur Data" in k1["panduan"]["teks"]
    assert k1["pembimbing_akademik"]["nama_lengkap"] == "Dosen PA"
    assert k1["pembimbing_akademik"]["email"] == "dosen@k.ac.id"


def test_panduan_baru_langsung_menjadi_dasar_dan_versi_tercatat(client, dunia, kampus):
    pid = kampus["prodi1"]["id"]
    _siapkan_panduan(client, dunia["h_kaprodi"], pid, "V1", TEKS_PANDUAN)
    baru = [*TEKS_PANDUAN, "Perubahan 2023: beban studi maksimal semester 3 menjadi 22 SKS untuk semua mahasiswa."]
    _siapkan_panduan(client, dunia["h_kaprodi"], pid, "V2", baru)
    k = client.get("/akademik/konteks", headers=dunia["h_mhs"]).json()
    assert k["panduan"]["versi"] == 2 and "22 SKS" in k["panduan"]["teks"]


def test_tanpa_teks_lebih_ringan(client, dunia, kampus):
    _siapkan_panduan(client, dunia["h_kaprodi"], kampus["prodi1"]["id"], "V1", TEKS_PANDUAN)
    k = client.get("/akademik/konteks", headers=dunia["h_mhs"], params={"tanpa_teks": True}).json()
    assert "teks" not in k["panduan"] and k["panduan"]["teks_karakter"] > 200


def test_staf_wajib_prodi_id_dan_dibatasi_cakupan(client, dunia, kampus, admin):
    _siapkan_panduan(client, dunia["h_kaprodi"], kampus["prodi1"]["id"], "V1", TEKS_PANDUAN)
    p1, p2, p3 = kampus["prodi1"]["id"], kampus["prodi2"]["id"], dunia["prodi3"]["id"]
    assert client.get("/akademik/konteks", headers=dunia["h_kaprodi"]).status_code == 403
    assert client.get("/akademik/konteks", headers=dunia["h_kaprodi"], params={"prodi_id": p1}).status_code == 200
    # Kaprodi prodi1 tidak melihat prodi2 maupun prodi di fakultas lain.
    assert client.get("/akademik/konteks", headers=dunia["h_kaprodi"], params={"prodi_id": p2}).status_code == 404
    assert client.get("/akademik/konteks", headers=dunia["h_dekan"], params={"prodi_id": p3}).status_code == 404
    assert client.get("/akademik/konteks", headers=admin, params={"prodi_id": p1}).status_code == 200


def test_mahasiswa_tidak_bisa_mengintip_prodi_lain_lewat_parameter(client, dunia, kampus):
    _siapkan_panduan(client, dunia["h_kaprodi"], kampus["prodi1"]["id"], "V1", TEKS_PANDUAN)
    # mhs2 (prodi2) mencoba meminta prodi1: parameter diabaikan, tetap prodinya sendiri (tanpa panduan -> 404).
    r = client.get("/akademik/konteks", headers=dunia["h_mhs2"], params={"prodi_id": kampus["prodi1"]["id"]})
    assert r.status_code == 404 and "Informatika Internasional" in r.json()["detail"]


def test_konteks_butuh_token(client):
    assert client.get("/akademik/konteks").status_code == 401


def test_mahasiswa_tanpa_pa_tetap_dapat_konteks(client, dunia, kampus, admin):
    _siapkan_panduan(client, admin, kampus["prodi2"]["id"], "IP", TEKS_PANDUAN)
    k = client.get("/akademik/konteks", headers=dunia["h_mhs2"]).json()
    assert k["prodi"]["kode"] == "IF-IP" and k["pembimbing_akademik"] is None
