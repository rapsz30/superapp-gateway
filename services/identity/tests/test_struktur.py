from __future__ import annotations

import uuid


def test_bangun_pohon_dan_baca(client, admin, kampus):
    pohon = client.get("/struktur", headers=admin).json()
    assert len(pohon) == 1
    fak = pohon[0]
    assert fak["kode"] == "FTI"
    assert [p["kode"] for p in fak["jurusan"][0]["prodi"]] == ["IF-IP", "IF-S1"]


def test_kode_unik_pada_tingkatnya(client, admin, kampus):
    f, j = kampus["fakultas"], kampus["jurusan"]
    r = client.post("/fakultas", json={"kode": "FTI", "nama": "Lain"}, headers=admin)
    assert r.status_code == 409 and "Kode fakultas" in r.json()["detail"]
    r = client.post("/jurusan", json={"fakultas_id": f["id"], "kode": "IF", "nama": "Lain"}, headers=admin)
    assert r.status_code == 409
    r = client.post("/prodi", json={"jurusan_id": j["id"], "kode": "IF-S1", "nama": "Lain"}, headers=admin)
    assert r.status_code == 409
    # Kode yang sama boleh di induk lain.
    f2 = client.post("/fakultas", json={"kode": "FH", "nama": "Hukum"}, headers=admin).json()
    j2 = client.post("/jurusan", json={"fakultas_id": f2["id"], "kode": "IF", "nama": "Lain"}, headers=admin)
    assert j2.status_code == 201


def test_induk_wajib_ada_dan_aktif(client, admin, kampus):
    r = client.post("/jurusan", json={"fakultas_id": str(uuid.uuid4()), "kode": "X", "nama": "X"}, headers=admin)
    assert r.status_code == 400
    r = client.post("/prodi", json={"jurusan_id": str(uuid.uuid4()), "kode": "X", "nama": "X"}, headers=admin)
    assert r.status_code == 400


def test_validasi_masukan(client, admin):
    assert client.post("/fakultas", json={"kode": "spasi salah", "nama": "X"}, headers=admin).status_code == 422
    assert client.post("/fakultas", json={"kode": "OK", "nama": " "}, headers=admin).status_code == 422
    assert client.post("/fakultas", json={"kode": "OK", "nama": "X", "tambahan": 1}, headers=admin).status_code == 422
    assert client.post("/prodi", json={"jurusan_id": str(uuid.uuid4()), "kode": "X", "nama": "X", "jenjang": "S9"}, headers=admin).status_code == 422


def test_tutup_unit_ditolak_bila_masih_punya_anak(client, admin, kampus):
    f, j, p1 = kampus["fakultas"], kampus["jurusan"], kampus["prodi1"]
    r = client.patch(f"/fakultas/{f['id']}", json={"aktif": False}, headers=admin)
    assert r.status_code == 409 and "jurusan aktif" in r.json()["detail"]
    r = client.patch(f"/jurusan/{j['id']}", json={"aktif": False}, headers=admin)
    assert r.status_code == 409 and "prodi aktif" in r.json()["detail"]

    # Tutup dari bawah ke atas berhasil.
    for p in (kampus["prodi1"], kampus["prodi2"]):
        assert client.patch(f"/prodi/{p['id']}", json={"aktif": False}, headers=admin).status_code == 200
    assert client.patch(f"/jurusan/{j['id']}", json={"aktif": False}, headers=admin).status_code == 200
    assert client.patch(f"/fakultas/{f['id']}", json={"aktif": False}, headers=admin).status_code == 200

    # Tidak bisa membuka anak saat induk tertutup, dan tidak bisa membuat anak baru.
    assert client.patch(f"/prodi/{p1['id']}", json={"aktif": True}, headers=admin).status_code == 409
    assert client.post("/jurusan", json={"fakultas_id": f["id"], "kode": "N", "nama": "N"}, headers=admin).status_code == 409


def test_tutup_prodi_ditolak_bila_ada_mahasiswa_atau_penugasan(client, admin, kampus, db):
    from tests.conftest import buat_orang_akun

    p1 = kampus["prodi1"]
    kp = buat_orang_akun(db, "Kaprodi", "kp@kampus.ac.id")
    r = client.post(
        "/penugasan",
        json={"orang_id": str(kp.id), "peran": "kaprodi", "unit_tipe": "prodi", "unit_id": p1["id"]},
        headers=admin,
    )
    assert r.status_code == 201
    r = client.patch(f"/prodi/{p1['id']}", json={"aktif": False}, headers=admin)
    assert r.status_code == 409 and "penugasan aktif" in r.json()["detail"]

    anggota = client.post("/orang", json={"nama_lengkap": "Mhs", "nim": "1"}, headers=admin).json()
    # Akhiri kaprodi lebih dulu, lalu uji mahasiswa aktif.
    pid = client.get("/penugasan", headers=admin, params={"unit_id": p1["id"]}).json()["data"][0]["id"]
    assert client.post(f"/penugasan/{pid}/akhiri", json={}, headers=admin).status_code == 200
    assert client.post(
        "/keanggotaan", json={"orang_id": anggota["id"], "prodi_id": p1["id"], "angkatan": 2024}, headers=admin
    ).status_code == 201
    r = client.patch(f"/prodi/{p1['id']}", json={"aktif": False}, headers=admin)
    assert r.status_code == 409 and "1 mahasiswa" in r.json()["detail"]


def test_tidak_ada_endpoint_hapus(client, admin, kampus):
    for jalur in ("fakultas", "jurusan", "prodi"):
        uid = kampus[{"fakultas": "fakultas", "jurusan": "jurusan", "prodi": "prodi1"}[jalur]]["id"]
        assert client.delete(f"/{jalur}/{uid}", headers=admin).status_code == 405


def test_perubahan_tercatat_di_audit(client, admin, kampus):
    f = kampus["fakultas"]
    client.patch(f"/fakultas/{f['id']}", json={"nama": "Nama Baru"}, headers=admin)
    log = client.get("/audit", headers=admin, params={"objek_id": f["id"]}).json()["data"]
    aksi = [x["aksi"] for x in log]
    assert aksi == ["fakultas.ubah", "fakultas.buat"]
    ubah = log[0]
    assert ubah["sebelum"]["nama"] == "Fakultas Teknologi Industri"
    assert ubah["sesudah"]["nama"] == "Nama Baru"


def test_paginasi(client, admin):
    for i in range(5):
        client.post("/fakultas", json={"kode": f"F{i}", "nama": f"F{i}"}, headers=admin)
    r = client.get("/fakultas", headers=admin, params={"ukuran": 2, "halaman": 2}).json()
    assert r["total"] == 5 and [x["kode"] for x in r["data"]] == ["F2", "F3"]
    assert client.get("/fakultas", headers=admin, params={"ukuran": 500}).status_code == 422
