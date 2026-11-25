from __future__ import annotations

import io
import threading

import pytest
from sqlalchemy import select

from src.models import Akun, Orang, Penugasan
from tests.conftest import PDF_PANDUAN, SANDI, buat_pdf, masuk
from tests.test_hak_akses import siapkan_dunia

PDF = PDF_PANDUAN


@pytest.fixture
def dunia(client, db, admin, kampus):
    return siapkan_dunia(client, db, admin, kampus)


def _unggah(client, h, prodi_id, judul="Panduan 2021", isi=PDF, nama="panduan.pdf"):
    return client.post(
        f"/prodi/{prodi_id}/panduan",
        data={"judul": judul},
        files={"berkas": (nama, io.BytesIO(isi), "application/pdf")},
        headers=h,
    )


# ---------------- Panduan ----------------
def test_alur_versi_panduan(client, dunia, kampus):
    pid = kampus["prodi1"]["id"]
    kp = dunia["h_kaprodi"]
    v1 = _unggah(client, kp, pid)
    assert v1.status_code == 201 and v1.json()["versi"] == 1 and v1.json()["status"] == "draf"
    # Belum ada yang aktif.
    assert client.get(f"/prodi/{pid}/panduan/aktif", headers=dunia["h_mhs"]).status_code == 404

    assert client.post(f"/panduan/{v1.json()['id']}/aktifkan", headers=kp).json()["status"] == "aktif"
    v2 = _unggah(client, kp, pid, judul="Panduan 2023").json()
    assert v2["versi"] == 2
    # Versi lama masih aktif sampai v2 diaktifkan.
    assert client.get(f"/prodi/{pid}/panduan/aktif", headers=kp).json()["versi"] == 1
    client.post(f"/panduan/{v2['id']}/aktifkan", headers=kp)
    assert client.get(f"/prodi/{pid}/panduan/aktif", headers=kp).json()["versi"] == 2

    daftar = client.get(f"/prodi/{pid}/panduan", headers=dunia["h_mhs"]).json()["data"]
    assert [(x["versi"], x["status"]) for x in daftar] == [(2, "aktif"), (1, "diarsipkan")]

    # Versi lama tetap bisa diunduh, dan bisa diaktifkan kembali.
    unduh = client.get(f"/panduan/{v1.json()['id']}/berkas", headers=dunia["h_mhs"])
    assert unduh.status_code == 200 and unduh.content == PDF
    client.post(f"/panduan/{v1.json()['id']}/aktifkan", headers=kp)
    assert client.get(f"/prodi/{pid}/panduan/aktif", headers=kp).json()["versi"] == 1


def test_panduan_hak_dan_validasi(client, dunia, kampus, admin):
    pid, pid2 = kampus["prodi1"]["id"], kampus["prodi2"]["id"]
    assert _unggah(client, dunia["h_kaprodi"], pid2).status_code == 403  # prodi lain
    assert _unggah(client, dunia["h_dosen"], pid).status_code == 403
    assert _unggah(client, dunia["h_mhs"], pid).status_code == 403
    assert _unggah(client, admin, pid).status_code == 201  # superadmin boleh
    assert _unggah(client, dunia["h_kaprodi"], pid, isi=b"bukan pdf").status_code == 400
    # PDF tanpa teks (hasil scan) dan PDF rusak ditolak dengan pesan yang jelas.
    scan = _unggah(client, dunia["h_kaprodi"], pid, isi=buat_pdf(None))
    assert scan.status_code == 422 and "scan" in scan.json()["detail"]
    rusak = _unggah(client, dunia["h_kaprodi"], pid, isi=b"%PDF-1.4 rusak total")
    assert rusak.status_code == 422
    assert _unggah(client, dunia["h_kaprodi"], "00000000-0000-0000-0000-000000000000").status_code in (403, 404)
    gid = client.get(f"/prodi/{pid}/panduan", headers=admin).json()["data"][0]["id"]
    assert client.post(f"/panduan/{gid}/aktifkan", headers=dunia["h_dosen"]).status_code == 403


def test_aktivasi_bersamaan_tetap_satu_aktif(client, dunia, kampus, db):
    from src.models import PanduanAkademik

    pid = kampus["prodi1"]["id"]
    ids = [_unggah(client, dunia["h_kaprodi"], pid, judul=f"V{i}").json()["id"] for i in range(4)]
    hasil: list[int] = []

    def aktifkan(gid):
        hasil.append(client.post(f"/panduan/{gid}/aktifkan", headers=dunia["h_kaprodi"]).status_code)

    ts = [threading.Thread(target=aktifkan, args=(g,)) for g in ids]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert all(s == 200 for s in hasil), hasil
    aktif = db.scalars(select(PanduanAkademik).where(PanduanAkademik.status == "aktif")).all()
    assert len(aktif) == 1


def test_path_traversal_pada_unduhan_ditolak(client, dunia, kampus, db, admin):
    from src.models import PanduanAkademik

    g = _unggah(client, admin, kampus["prodi1"]["id"]).json()
    obj = db.get(PanduanAkademik, g["id"])
    obj.berkas_path = "../../../../Windows/win.ini"
    db.commit()
    assert client.get(f"/panduan/{g['id']}/berkas", headers=admin).status_code == 404


# ---------------- Impor CSV ----------------
def _impor(client, h, teks: str):
    return client.post("/orang/impor", files={"berkas": ("data.csv", io.BytesIO(teks.encode()), "text/csv")}, headers=h)


def test_impor_laporan_per_baris(client, admin, kampus, db):
    csv_teks = (
        "nama_lengkap,nim,nidn,email_kontak,email_akun,prodi,angkatan\n"
        "Alya Wijaya,20110001,,alya@x.ac.id,Alya.Wijaya@kampus.ac.id,FTI/IF/IF-S1,2024\n"
        "Bima Pratama,20110002,,,,FTI/IF/IF-S1,2024\n"
        "NIM Kembar,20110001,,,,FTI/IF/IF-S1,2024\n"          # NIM duplikat
        ",20110009,,,,,\n"                                    # nama kosong
        "Prodi Salah,20110010,,,,FTI/IF/TIDAKADA,2024\n"
        "Email Rusak,20110011,,bukan-email,,,\n"
        "Dosen Satu,,0011223344,,dosen1@kampus.ac.id,,\n"
    )
    r = _impor(client, admin, csv_teks)
    assert r.status_code == 200, r.text
    hasil = r.json()
    assert (hasil["total"], hasil["berhasil"], hasil["gagal"]) == (7, 3, 4)
    per = {b["baris"]: b for b in hasil["baris"]}
    assert per[2]["status"] == "ok" and per[2]["email"] == "alya.wijaya@kampus.ac.id" and per[2]["sandi_sementara"]
    assert per[3]["status"] == "ok" and "sandi_sementara" not in per[3]
    assert per[4]["status"] == "gagal" and "NIM" in per[4]["alasan"]
    assert per[5]["status"] == "gagal" and "nama_lengkap" in per[5]["alasan"]
    assert per[6]["status"] == "gagal" and "tidak ditemukan" in per[6]["alasan"]
    assert per[7]["status"] == "gagal"
    assert per[8]["status"] == "ok"
    # Baris gagal tidak meninggalkan data setengah jadi.
    assert db.scalar(select(Orang).where(Orang.nama_lengkap == "Prodi Salah")) is None
    assert db.scalar(select(Orang).where(Orang.nama_lengkap == "NIM Kembar")) is None
    # Sandi sementara berfungsi dan memaksa ganti sandi.
    login = client.post("/auth/login", json={"email": "alya.wijaya@kampus.ac.id", "sandi": per[2]["sandi_sementara"]})
    assert login.status_code == 200 and login.json()["wajib_ganti_sandi"] is True
    assert login.json()["peran"] == ["mahasiswa"]


def test_impor_validasi_berkas_dan_hak(client, admin, dunia):
    assert _impor(client, dunia["h_kaprodi"], "nama_lengkap\nA\n").status_code == 403
    assert _impor(client, admin, "kolom_lain\nA\n").status_code == 400
    r = client.post("/orang/impor", files={"berkas": ("x.csv", io.BytesIO(b"\xff\xfe\x00bad"), "text/csv")}, headers=admin)
    assert r.status_code == 400
    besar = "nama_lengkap\n" + "\n".join(f"N{i}" for i in range(2001))
    assert _impor(client, admin, besar).status_code == 400


def test_sandi_sementara_tidak_masuk_audit(client, admin, kampus):
    _impor(client, admin, "nama_lengkap,email_akun\nRahasia,rahasia@kampus.ac.id\n")
    log = client.get("/audit", headers=admin, params={"ukuran": 200}).json()["data"]
    teks = str(log)
    assert "sandi_hash" not in teks and "sandi_sementara" not in teks


# ---------------- Akun ----------------
def test_buat_dan_atur_ulang_sandi(client, admin, db):
    o = client.post("/orang", json={"nama_lengkap": "Dosen Baru", "nidn": "123"}, headers=admin).json()
    a = client.post("/akun", json={"orang_id": o["id"], "email": "Baru@Kampus.ac.id"}, headers=admin)
    assert a.status_code == 201 and a.json()["email"] == "baru@kampus.ac.id" and a.json()["sandi_sementara"]
    assert client.post("/akun", json={"orang_id": o["id"], "email": "lain@kampus.ac.id"}, headers=admin).status_code == 409
    o2 = client.post("/orang", json={"nama_lengkap": "Dosen Dua"}, headers=admin).json()
    assert client.post("/akun", json={"orang_id": o2["id"], "email": "BARU@kampus.ac.id"}, headers=admin).status_code == 409
    assert client.post("/akun", json={"orang_id": o2["id"], "email": "d2@kampus.ac.id", "sandi": "pendek"}, headers=admin).status_code == 400

    reset = client.post(f"/akun/{a.json()['id']}/atur-ulang-sandi", headers=admin)
    assert reset.status_code == 200 and reset.json()["sandi_sementara"] != a.json()["sandi_sementara"]
    tanpa_peran = client.post("/auth/login", json={"email": "baru@kampus.ac.id", "sandi": reset.json()["sandi_sementara"]})
    assert tanpa_peran.status_code == 403  # sandi benar, tetapi belum punya peran aktif


# ---------------- CLI ----------------
def test_cli_buat_superadmin(db, capsys):
    from src.cli import main

    main(["buat-superadmin", "--email", "Root@Kampus.ac.id", "--nama", "Root"])
    keluar = capsys.readouterr().out
    assert "root@kampus.ac.id" in keluar and "Sandi sementara" in keluar
    akun = db.scalar(select(Akun).where(Akun.email == "root@kampus.ac.id"))
    assert akun is not None and akun.wajib_ganti_sandi is True
    pen = db.scalar(select(Penugasan).where(Penugasan.orang_id == akun.orang_id))
    assert pen.peran == "superadmin" and pen.unit_tipe == "global"
    with pytest.raises(SystemExit):
        main(["buat-superadmin", "--email", "root@kampus.ac.id", "--nama", "Dobel"])
    with pytest.raises(SystemExit):
        main(["buat-superadmin", "--email", "lain@kampus.ac.id", "--nama", "L", "--sandi", "pendek"])
