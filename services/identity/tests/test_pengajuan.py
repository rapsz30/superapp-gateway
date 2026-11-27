"""Pengajuan lewat proses AlurKerja lengkap: mode AlurKerja (Camunda REST dan matkul ditiru) dan mode lokal."""

from __future__ import annotations

import io
import json
import re

import httpx
import pytest
from sqlalchemy import select

from src.integrations import alurkerja
from src.integrations import matkul as modul_matkul
from src.integrations.alurkerja import AlurKerjaKlien
from src.integrations.matkul import MatkulGalat
from src.models import Pengajuan
from src.core.config import get_settings
from tests.conftest import INTERNAL_TOKEN, TEKS_PANDUAN, buat_orang_akun, buat_pdf, masuk
from tests.test_hak_akses import siapkan_dunia

KHS_PDF = buat_pdf(["KARTU HASIL STUDI", "Nama: Mahasiswa Satu", "NIM: 20110001"])


# ====================================================================== tiruan
class MatkulPalsu:
    """Layanan matkul tiruan. Mengembalikan hasil sesuai kontrak connector."""

    def __init__(self):
        self.keyakinan = 0.95
        self.nim_cocok = True
        self.gagal: set[str] = set()
        self.panggilan: list[tuple[str, tuple]] = []

    def _cek(self, nama: str, *args):
        self.panggilan.append((nama, args))
        if nama in self.gagal:
            raise MatkulGalat(f"{nama} gagal")

    def upload(self, isi, nama_berkas):
        self._cek("upload", nama_berkas)
        assert isi.startswith(b"%PDF-")
        return "file_1"

    def ekstraksi(self, khs_file_id, semester_target, id_pengajuan):
        self._cek("ekstraksi", khs_file_id, semester_target, id_pengajuan)
        return {
            "khs_ref": "khs_1", "ipk": 3.1, "sks_lulus": 40, "mk_lulus": ["IF101"], "mk_ulang": ["IF103"],
            "keyakinan": self.keyakinan, "prodi": "Informatika", "nim_cocok": self.nim_cocok,
        }

    def rekomendasi(self, khs_ref, semester_target):
        self._cek("rekomendasi", khs_ref, semester_target)
        return self._rencana("rnc_1")

    def ringkasan_khs(self, khs_ref):
        self._cek("ringkasan", khs_ref)
        return {"ipk": 3.1, "sks_lulus": 40, "per_semester": []}

    def revisi(self, rencana_ref, catatan_dosen):
        self._cek("revisi", rencana_ref, catatan_dosen)
        return self._rencana("rnc_2", catatan_dosen)

    @staticmethod
    def _rencana(ref, catatan=""):
        return {
            "rencana_ref": ref,
            "rencana_mk": [{"kode": "IF301", "nama": "Basis Data", "sks": 3, "alasan": f"uji {catatan}".strip()}],
            "total_sks": 3,
            "alasan": "Ringkasan uji.",
            "peringatan": ["IF103 belum lulus (nilai E), wajib diulang"],
        }


@pytest.fixture
def matkul_palsu(monkeypatch):
    m = MatkulPalsu()
    monkeypatch.setattr(modul_matkul, "dapatkan_matkul", lambda: m)
    return m


class Camunda:
    """Camunda REST tiruan yang meniru BPMN perencanaan-studi-superapp secukupnya.

    `aktif` = id aktivitas yang sedang berjalan. Metode bernama seperti kejadian di dunia nyata
    (worker menyelesaikan langkah AI, dosen memutuskan di Tasklist) dipanggil oleh tes.
    """

    TUGAS_MANUSIA = {"Task_Unggah", "Task_Periksa", "Task_Tinjau"}

    def __init__(self):
        self.proses: dict[str, dict] = {}
        self.permintaan: list[tuple[str, str, object]] = []
        self.mati = False
        self.tolak: set[str] = set()  # "mulai", "tugas", "assignee", "hapus", "variabel"

    def handler(self, req: httpx.Request) -> httpx.Response:
        if self.mati:
            raise httpx.ConnectError("mati", request=req)
        path = req.url.path.removeprefix("/engine-rest")
        body = json.loads(req.content) if req.content else None
        self.permintaan.append((req.method, path, body))
        q = req.url.params

        if req.method == "POST" and path.endswith("/start"):
            if "mulai" in self.tolak:
                return httpx.Response(500, json={})
            iid = f"inst-{len(self.proses) + 1}"
            self.proses[iid] = {
                "state": "ACTIVE",
                "vars": {k: v["value"] for k, v in body["variables"].items()},
                "aktif": ["Task_Unggah"],
                "insiden": None,
                "assignee_tinjau": body["variables"]["dosen_pa"]["value"],
            }
            return httpx.Response(200, json={"id": iid})
        if m := re.fullmatch(r"/history/process-instance/(.+)", path):
            p = self.proses.get(m.group(1))
            return httpx.Response(404, json={}) if p is None else httpx.Response(200, json={"state": p["state"]})
        if path == "/history/activity-instance":
            p = self.proses[q["processInstanceId"]]
            return httpx.Response(200, json=[{"activityId": a} for a in p["aktif"]])
        if path == "/history/variable-instance":
            p = self.proses[q["processInstanceId"]]
            return httpx.Response(200, json=[{"name": k, "value": v} for k, v in p["vars"].items()])
        if path == "/incident":
            p = self.proses[q["processInstanceId"]]
            return httpx.Response(200, json=[{"incidentMessage": p["insiden"]}] if p["insiden"] else [])
        m = re.fullmatch(r"/process-instance/([^/]+)/variables/(.+)", path)
        if m and req.method == "PUT":
            if "variabel" in self.tolak:
                return httpx.Response(500, json={})
            self.proses[m.group(1)]["vars"][m.group(2)] = body["value"]
            return httpx.Response(204)
        if m := re.fullmatch(r"/process-instance/(.+)", path):
            if req.method == "DELETE":
                if "hapus" in self.tolak:
                    return httpx.Response(500, json={})
                if m.group(1) in self.proses:
                    self.proses[m.group(1)]["state"] = "EXTERNALLY_TERMINATED"
                    self.proses[m.group(1)]["aktif"] = []
                return httpx.Response(204)
        if path == "/task":
            p = self.proses[q["processInstanceId"]]
            kunci = q.get("taskDefinitionKey")
            ada = [a for a in p["aktif"] if a in self.TUGAS_MANUSIA and (not kunci or a == kunci)]
            return httpx.Response(200, json=[{"id": f"{q['processInstanceId']}|{a}"} for a in ada])
        if m := re.fullmatch(r"/task/(.+)\|(.+)/complete", path):
            if "tugas" in self.tolak:
                return httpx.Response(500, json={})
            iid, kunci = m.group(1), m.group(2)
            p = self.proses[iid]
            for k, v in (body or {}).get("variables", {}).items():
                p["vars"][k] = v["value"]
            if kunci == "Task_Tinjau":
                setuju = p["vars"].get("keputusan") == "setuju"
                p["state"] = "COMPLETED" if setuju else "ACTIVE"
                p["aktif"] = [] if setuju else ["Task_Revisi"]
            else:
                p["aktif"] = {"Task_Unggah": ["Task_BacaKhs"], "Task_Periksa": ["Task_Rekom"]}[kunci]
            return httpx.Response(204)
        if m := re.fullmatch(r"/task/(.+)\|(.+)/assignee", path):
            if "assignee" in self.tolak:
                return httpx.Response(500, json={})
            self.proses[m.group(1)]["assignee_tinjau"] = body["userId"]
            return httpx.Response(204)
        return httpx.Response(404, json={})

    # ---- kejadian di dunia nyata ----
    def worker_ekstraksi(self, iid, keyakinan=0.95, nim_cocok=True):
        p = self.proses[iid]
        assert p["aktif"] == ["Task_BacaKhs"], p["aktif"]
        p["vars"].update(khs_ref="khs_1", ipk=3.1, sks_lulus=40, mk_lulus='["IF101"]', mk_ulang='["IF103"]',
                         keyakinan=keyakinan, prodi="Informatika", nim_cocok=nim_cocok)
        p["aktif"] = ["Task_Rekom"] if keyakinan >= 0.9 else ["Task_Periksa"]

    def worker_rekomendasi(self, iid):
        p = self.proses[iid]
        assert p["aktif"] == ["Task_Rekom"], p["aktif"]
        p["vars"].update(
            rencana_ref="rnc_1", total_sks=3, alasan="Ringkasan uji.", jumlah_revisi=0, ada_peringatan=True,
            rencana_mk='[{"kode":"IF301","nama":"Basis Data","sks":3,"alasan":"uji"}]',
            peringatan='["IF103 belum lulus (nilai E), wajib diulang"]',
        )
        p["aktif"] = ["Task_Tinjau"]

    def dosen_putuskan(self, iid, keputusan, catatan=None):
        p = self.proses[iid]
        assert p["aktif"] == ["Task_Tinjau"], p["aktif"]
        p["vars"]["keputusan"] = keputusan
        if catatan:
            p["vars"]["catatan_dosen"] = catatan
        if keputusan == "setuju":
            p["state"], p["aktif"] = "COMPLETED", []
        else:
            p["aktif"] = ["Task_Revisi"]

    def worker_revisi(self, iid):
        p = self.proses[iid]
        assert p["aktif"] == ["Task_Revisi"], p["aktif"]
        p["vars"].update(rencana_ref="rnc_2", jumlah_revisi=int(p["vars"].get("jumlah_revisi", 0)) + 1)
        p["aktif"] = ["Task_Tinjau"]


@pytest.fixture
def camunda(monkeypatch):
    c = Camunda()
    klien = AlurKerjaKlien(
        "https://alurkerja.test", "svc", "p", "perencanaan-studi-superapp", tenant_id="tenant-1",
        http=httpx.Client(transport=httpx.MockTransport(c.handler)),
    )
    monkeypatch.setattr(alurkerja, "dapatkan_klien", lambda: klien)
    return c


# ====================================================================== pembantu
@pytest.fixture
def siap(client, db, admin, kampus, matkul_palsu):
    d = siapkan_dunia(client, db, admin, kampus)
    r = client.post(
        f"/prodi/{kampus['prodi1']['id']}/panduan",
        data={"judul": "Panduan IF"},
        files={"berkas": ("p.pdf", io.BytesIO(buat_pdf(TEKS_PANDUAN)), "application/pdf")},
        headers=d["h_kaprodi"],
    )
    client.post(f"/panduan/{r.json()['id']}/aktifkan", headers=d["h_kaprodi"])
    d.update(panduan=r.json(), admin=admin, kampus=kampus, matkul=matkul_palsu)
    return d


def ajukan(client, d, semester=3, isi=KHS_PDF, nama="khs.pdf", headers=None):
    return client.post(
        "/pengajuan",
        data={"semester_target": str(semester)},
        files={"berkas": (nama, io.BytesIO(isi), "application/pdf")},
        headers=headers or d["h_mhs"],
    )


def test_catatan_ai_pakai_pengajuan_id_dan_menampilkan_mahasiswa(client, siap, monkeypatch):
    """Catatan dari worker proses dipetakan ke akun mahasiswa pemilik pengajuan."""
    token = "t" * 40
    monkeypatch.setattr(get_settings(), "ai_catat_token", token)
    pengajuan = ajukan(client, siap).json()
    catatan = client.post("/internal/ai-pemakaian", json={
        "layanan": "matkul", "fitur": "rekomendasi_matkul", "model": "gpt-6-luna",
        "pengajuan_id": pengajuan["id"],
    }, headers={"X-AI-Token": token})
    assert catatan.status_code == 204
    hasil = client.get("/ai-pemakaian", headers=siap["admin"]).json()
    assert any(p["email"] == "mhs@k.ac.id" and p["panggilan"] == 1 for p in hasil["per_pengguna"])


def ambil(client, d, pid, who="h_mhs"):
    r = client.get(f"/pengajuan/{pid}", headers=d[who])
    assert r.status_code == 200, r.text
    return r.json()


# ====================================================================== mode AlurKerja
def test_ajukan_memulai_proses_dan_menyelesaikan_tugas_unggah(client, siap, camunda):
    r = ajukan(client, siap)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["mode"] == "alurkerja" and p["status"] == "diajukan" and p["tahap"] == "ekstraksi"
    assert p["dpa"]["nama_lengkap"] == "Dosen PA" and p["panduan"]["versi"] == 1

    mulai = next(x for x in camunda.permintaan if x[1].endswith("/start"))
    assert mulai[1] == "/process-definition/key/perencanaan-studi-superapp/tenant-id/tenant-1/start"
    v = {k: x["value"] for k, x in mulai[2]["variables"].items()}
    assert mulai[2]["businessKey"] == p["id"]
    assert v["dosen_pa"] == "dosen@k.ac.id"            # email dosen, huruf kecil
    assert v["initiator"] == "svc"                      # pemilik tugas mahasiswa di BPMN
    assert v["nim_mahasiswa"] == "20110001" and v["khs_file_id"] == "file_1" and v["id_pengajuan"] == p["id"]
    assert v["semester_target"] == 3 and v["versi_panduan"] == 1
    assert "Mahasiswa Satu" not in json.dumps(mulai[2])  # nama mahasiswa tidak dikirim ke AlurKerja
    # Tugas "Unggah KHS" diselesaikan atas nama mahasiswa, sehingga proses lanjut ke langkah AI.
    assert camunda.proses["inst-1"]["aktif"] == ["Task_BacaKhs"]
    assert siap["matkul"].panggilan == [("upload", ("khs.pdf",))]


def test_alur_normal_sampai_disetujui(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]

    camunda.worker_ekstraksi("inst-1", keyakinan=0.95)
    d = ambil(client, siap, pid)
    assert d["tahap"] == "rekomendasi" and d["hasil_bacaan"]["ipk"] == 3.1
    assert d["hasil_bacaan"]["mk_ulang"] == ["IF103"]  # variabel JSON diurai
    assert [x["keadaan"] for x in d["langkah"]] == ["selesai", "aktif", "menunggu"]

    camunda.worker_rekomendasi("inst-1")
    d = ambil(client, siap, pid)
    assert d["tahap"] == "tinjau"
    assert d["rencana"]["rencana_mk"][0]["kode"] == "IF301" and d["rencana"]["total_sks"] == 3
    assert d["rencana"]["peringatan"] == ["IF103 belum lulus (nilai E), wajib diulang"]
    assert d["langkah"][2]["keterangan"] == "Menunggu keputusan pembimbing akademik"

    # DPA melihat pengajuan ini dengan isi untuk ditinjau.
    daftar = client.get("/pengajuan", headers=siap["h_dosen"]).json()
    assert daftar["total"] == 1 and daftar["data"][0]["tahap"] == "tinjau"

    camunda.dosen_putuskan("inst-1", "setuju", "Silakan lanjut.")
    d = ambil(client, siap, pid)
    assert d["status"] == "disetujui" and d["tahap"] == "selesai" and d["catatan_dpa"] == "Silakan lanjut."
    assert [x["keadaan"] for x in d["langkah"]] == ["selesai"] * 3
    # Sudah final: tidak ditanyakan lagi ke AlurKerja.
    n = len(camunda.permintaan)
    ambil(client, siap, pid)
    assert len(camunda.permintaan) == n


def test_keyakinan_rendah_menunggu_pemeriksaan_mahasiswa(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    camunda.worker_ekstraksi("inst-1", keyakinan=0.7)
    d = ambil(client, siap, pid)
    assert d["tahap"] == "periksa" and d["langkah"][0]["keterangan"].startswith("Menunggu Anda")

    # Hanya pengaju yang boleh memeriksa.
    assert client.post(f"/pengajuan/{pid}/periksa", headers=siap["h_dosen"]).status_code == 403
    r = client.post(f"/pengajuan/{pid}/periksa", headers=siap["h_mhs"])
    assert r.status_code == 200 and r.json()["tahap"] == "rekomendasi"
    assert camunda.proses["inst-1"]["aktif"] == ["Task_Rekom"]
    # Sudah lewat langkah periksa.
    assert client.post(f"/pengajuan/{pid}/periksa", headers=siap["h_mhs"]).status_code == 409


def test_khs_dengan_nim_berbeda_tetap_bisa_dikonfirmasi(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    camunda.worker_ekstraksi("inst-1", keyakinan=0, nim_cocok=False)
    d = ambil(client, siap, pid)
    assert d["tahap"] == "periksa" and d["hasil_bacaan"]["nim_cocok"] is False
    r = client.post(f"/pengajuan/{pid}/periksa", headers=siap["h_mhs"])
    assert r.status_code == 200 and r.json()["tahap"] == "rekomendasi"
    assert camunda.proses["inst-1"]["aktif"] == ["Task_Rekom"]


def test_siklus_revisi_dari_catatan_dosen(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    camunda.worker_ekstraksi("inst-1")
    camunda.worker_rekomendasi("inst-1")

    camunda.dosen_putuskan("inst-1", "revisi", "Maksimal 18 SKS.")
    d = ambil(client, siap, pid)
    assert d["status"] == "diajukan" and d["tahap"] == "revisi" and d["catatan_dpa"] == "Maksimal 18 SKS."
    assert d["langkah"][2]["keterangan"] == "Rencana direvisi sesuai catatan pembimbing"

    camunda.worker_revisi("inst-1")
    d = ambil(client, siap, pid)
    assert d["tahap"] == "tinjau" and d["jumlah_revisi"] == 1

    camunda.dosen_putuskan("inst-1", "setuju")
    assert ambil(client, siap, pid)["status"] == "disetujui"


def test_langkah_ai_gagal_terlihat_sebagai_pesan_galat(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    camunda.proses["inst-1"]["insiden"] = "boom: LLM tidak menjawab"
    d = ambil(client, siap, pid)
    assert d["pesan_galat"] == "boom: LLM tidak menjawab" and d["langkah"][0]["keadaan"] == "galat"
    camunda.proses["inst-1"]["insiden"] = None
    assert ambil(client, siap, pid)["pesan_galat"] is None


def test_proses_dihentikan_dari_alurkerja_menjadi_dibatalkan(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    camunda.proses["inst-1"].update(state="EXTERNALLY_TERMINATED", aktif=[])
    d = ambil(client, siap, pid)
    assert d["status"] == "dibatalkan" and "EXTERNALLY_TERMINATED" in d["catatan_dpa"]
    camunda.proses.clear()
    assert ajukan(client, siap).status_code == 201  # tidak ada sisa yang menghalangi


def test_galat_jaringan_saat_sinkron_tidak_merusak_pembacaan(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    camunda.mati = True
    r = client.get(f"/pengajuan/{pid}", headers=siap["h_mhs"])
    assert r.status_code == 200 and r.json()["status"] == "diajukan"
    assert client.get("/pengajuan", headers=siap["h_mhs"]).status_code == 200


def test_kegagalan_saat_memulai_tidak_menyisakan_apa_pun(client, siap, camunda, db):
    camunda.mati = True
    r = ajukan(client, siap)
    assert r.status_code == 502 and "AlurKerja" in r.json()["detail"]
    assert db.scalar(select(Pengajuan.id)) is None
    camunda.mati = False

    camunda.tolak = {"mulai"}
    assert ajukan(client, siap).status_code == 502
    assert db.scalar(select(Pengajuan.id)) is None

    # Proses sudah berjalan tetapi tugas unggah gagal: proses dihentikan (tidak ada proses yatim).
    camunda.tolak = {"tugas"}
    assert ajukan(client, siap).status_code == 502
    assert db.scalar(select(Pengajuan.id)) is None
    assert camunda.proses["inst-1"]["state"] == "EXTERNALLY_TERMINATED"

    camunda.tolak = set()
    siap["matkul"].gagal = {"upload"}
    r = ajukan(client, siap)
    assert r.status_code == 502 and "rekomendasi" in r.json()["detail"]
    assert db.scalar(select(Pengajuan.id)) is None
    siap["matkul"].gagal = set()
    assert ajukan(client, siap).status_code == 201


def test_batalkan_menghentikan_proses_dan_gagal_dengan_aman(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    camunda.tolak = {"hapus"}
    assert client.post(f"/pengajuan/{pid}/batalkan", headers=siap["h_mhs"]).status_code == 502
    assert ambil(client, siap, pid)["status"] == "diajukan"
    camunda.tolak = set()
    assert client.post(f"/pengajuan/{pid}/batalkan", headers=siap["h_dosen"]).status_code == 403
    assert client.post(f"/pengajuan/{pid}/batalkan", headers=siap["h_mhs"]).json()["status"] == "dibatalkan"
    assert camunda.proses["inst-1"]["state"] == "EXTERNALLY_TERMINATED"
    assert client.post(f"/pengajuan/{pid}/batalkan", headers=siap["h_mhs"]).status_code == 409


def sampai_tinjau(client, d, camunda):
    pid = ajukan(client, d).json()["id"]
    camunda.worker_ekstraksi("inst-1")
    camunda.worker_rekomendasi("inst-1")
    return pid


def putuskan(client, d, pid, who="h_dosen", **isi):
    return client.post(f"/pengajuan/{pid}/keputusan", json=isi, headers=d[who])


def test_dosen_menyetujui_dari_aplikasi_menyelesaikan_tugas_alurkerja(client, siap, camunda):
    pid = sampai_tinjau(client, siap, camunda)
    r = putuskan(client, siap, pid, keputusan="setuju", catatan="  Silakan lanjut.  ")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "disetujui" and r.json()["catatan_dpa"] == "Silakan lanjut."
    p = camunda.proses["inst-1"]
    assert p["state"] == "COMPLETED"
    assert p["vars"]["keputusan"] == "setuju" and p["vars"]["catatan_dosen"] == "Silakan lanjut."
    assert putuskan(client, siap, pid, keputusan="setuju").status_code == 409


def test_dosen_meminta_revisi_dari_aplikasi_lalu_menyetujui(client, siap, camunda):
    pid = sampai_tinjau(client, siap, camunda)
    assert putuskan(client, siap, pid, keputusan="revisi").status_code == 400  # catatan wajib
    assert camunda.proses["inst-1"]["aktif"] == ["Task_Tinjau"]

    r = putuskan(client, siap, pid, keputusan="revisi", catatan="Maksimal 18 SKS.")
    assert r.status_code == 200 and r.json()["tahap"] == "revisi"
    assert camunda.proses["inst-1"]["aktif"] == ["Task_Revisi"]
    assert putuskan(client, siap, pid, keputusan="setuju").status_code == 409  # rencana sedang direvisi
    assert siap["matkul"].panggilan == [("upload", ("khs.pdf",))]  # revisi dikerjakan worker, bukan identity

    camunda.worker_revisi("inst-1")
    assert putuskan(client, siap, pid, keputusan="setuju").json()["status"] == "disetujui"
    assert camunda.proses["inst-1"]["vars"]["catatan_dosen"] == ""  # catatan lama tidak tertinggal


def test_keputusan_alurkerja_hanya_oleh_dpa_dan_gagal_dengan_aman(client, siap, camunda):
    pid = sampai_tinjau(client, siap, camunda)
    assert putuskan(client, siap, pid, who="h_mhs", keputusan="setuju").status_code == 403
    assert putuskan(client, siap, pid, who="h_kaprodi", keputusan="setuju").status_code == 403

    camunda.tolak = {"tugas"}
    r = putuskan(client, siap, pid, keputusan="setuju")
    assert r.status_code == 502 and "AlurKerja" in r.json()["detail"]
    camunda.tolak = set()
    camunda.mati = True
    assert putuskan(client, siap, pid, keputusan="setuju").status_code == 502
    camunda.mati = False
    assert ambil(client, siap, pid)["status"] == "diajukan"
    assert camunda.proses["inst-1"]["aktif"] == ["Task_Tinjau"]


def test_keputusan_alurkerja_ditolak_bila_belum_tahap_tinjau(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    assert putuskan(client, siap, pid, keputusan="setuju").status_code == 409
    assert camunda.proses["inst-1"]["aktif"] == ["Task_BacaKhs"]


def test_ganti_dpa_memindahkan_variabel_dan_tugas(client, siap, camunda, db, kampus):
    ajukan(client, siap)
    camunda.worker_ekstraksi("inst-1")
    camunda.worker_rekomendasi("inst-1")  # tugas tinjauan sudah terbuka untuk DPA lama
    pa2 = buat_orang_akun(db, "PA Dua", "PA2@K.ac.id")
    client.post("/penugasan", json={"orang_id": str(pa2.id), "peran": "dosen_pa", "unit_tipe": "prodi", "unit_id": kampus["prodi1"]["id"]}, headers=siap["admin"])
    r = client.post("/bimbingan/pindahkan", json={"dosen_asal_id": str(siap["orang"]["dosen"].id), "dosen_tujuan_id": str(pa2.id)}, headers=siap["h_kaprodi"])
    assert r.status_code == 200
    p = camunda.proses["inst-1"]
    assert p["vars"]["dosen_pa"] == "pa2@k.ac.id"       # dipakai tugas tinjauan berikutnya (mis. setelah revisi)
    assert p["assignee_tinjau"] == "pa2@k.ac.id"        # tugas yang sudah terbuka


def test_ganti_dpa_gagal_di_alurkerja_membatalkan_seluruh_operasi(client, siap, camunda, db, kampus):
    ajukan(client, siap)
    pa2 = buat_orang_akun(db, "PA Dua", "pa2@k.ac.id")
    client.post("/penugasan", json={"orang_id": str(pa2.id), "peran": "dosen_pa", "unit_tipe": "prodi", "unit_id": kampus["prodi1"]["id"]}, headers=siap["admin"])
    camunda.tolak = {"variabel"}
    r = client.post("/bimbingan/pindahkan", json={"dosen_asal_id": str(siap["orang"]["dosen"].id), "dosen_tujuan_id": str(pa2.id)}, headers=siap["h_kaprodi"])
    assert r.status_code == 502
    b = client.get("/bimbingan", headers=siap["admin"], params={"aktif": True}).json()["data"]
    assert b[0]["dosen_id"] == str(siap["orang"]["dosen"].id)
    assert client.get("/pengajuan", headers=siap["h_dosen"]).json()["total"] == 1


def test_lulus_menghentikan_proses_alurkerja(client, siap, camunda):
    ajukan(client, siap)
    k = client.get("/keanggotaan", headers=siap["admin"], params={"orang_id": str(siap["orang"]["mhs"].id), "aktif": True}).json()["data"][0]
    assert client.post(f"/keanggotaan/{k['id']}/status", json={"status": "lulus"}, headers=siap["h_kaprodi"]).status_code == 200
    assert camunda.proses["inst-1"]["state"] == "EXTERNALLY_TERMINATED"


# ====================================================================== konteks untuk matkul
def test_konteks_pengajuan_untuk_matkul(client, siap, camunda, kampus):
    pid = ajukan(client, siap).json()["id"]
    url = f"/internal/pengajuan/{pid}/konteks"
    assert client.get(url).status_code == 404
    assert client.get(url, headers={"X-Internal-Token": "salah"}).status_code == 404

    k = client.get(url, headers={"X-Internal-Token": INTERNAL_TOKEN}).json()
    assert k["mahasiswa"]["nim"] == "20110001" and k["prodi"]["kode"] == "IF-S1"
    assert k["panduan"]["versi"] == 1 and "Struktur Data" in k["panduan"]["teks"]
    assert k["prodi"]["maks_sks_semester"] is None  # bawaan layanan rekomendasi

    # Kaprodi menetapkan batas SKS prodi dan mengaktifkan panduan baru: konteks mengikuti, versi tercatat di pengajuan.
    client.patch(f"/prodi/{kampus['prodi1']['id']}", json={"maks_sks_semester": 20}, headers=siap["admin"])
    baru = client.post(
        f"/prodi/{kampus['prodi1']['id']}/panduan",
        data={"judul": "V2"},
        files={"berkas": ("p.pdf", io.BytesIO(buat_pdf([*TEKS_PANDUAN, "Versi dua dengan batas baru yang cukup panjang."])), "application/pdf")},
        headers=siap["h_kaprodi"],
    ).json()
    client.post(f"/panduan/{baru['id']}/aktifkan", headers=siap["h_kaprodi"])
    k = client.get(url, headers={"X-Internal-Token": INTERNAL_TOKEN}).json()
    assert k["panduan"]["versi"] == 2 and k["prodi"]["maks_sks_semester"] == 20
    assert ambil(client, siap, pid)["panduan"]["versi"] == 2

    assert client.get("/internal/pengajuan/00000000-0000-0000-0000-000000000000/konteks", headers={"X-Internal-Token": INTERNAL_TOKEN}).status_code == 404


def test_batas_sks_prodi_divalidasi(client, siap, kampus):
    assert client.patch(f"/prodi/{kampus['prodi1']['id']}", json={"maks_sks_semester": 0}, headers=siap["admin"]).status_code == 422
    assert client.patch(f"/prodi/{kampus['prodi1']['id']}", json={"maks_sks_semester": 99}, headers=siap["admin"]).status_code == 422
    ok = client.patch(f"/prodi/{kampus['prodi1']['id']}", json={"maks_sks_semester": 18}, headers=siap["admin"])
    assert ok.status_code == 200 and ok.json()["maks_sks_semester"] == 18
    kosong = client.patch(f"/prodi/{kampus['prodi1']['id']}", json={"maks_sks_semester": None}, headers=siap["admin"])
    assert kosong.json()["maks_sks_semester"] is None


# ====================================================================== validasi dan hak (tanpa AlurKerja = mode lokal)
def test_validasi_pengajuan(client, siap, db):
    assert ajukan(client, siap, isi=b"bukan pdf").status_code == 400
    assert ajukan(client, siap, semester=0).status_code == 422
    assert ajukan(client, siap, semester=15).status_code == 422
    assert ajukan(client, siap, headers=siap["h_dosen"]).status_code == 403
    besar = b"%PDF-" + b"0" * (15 * 1024 * 1024 + 1)
    assert ajukan(client, siap, isi=besar).status_code == 413
    assert db.scalar(select(Pengajuan.id)) is None


def test_prodi_tanpa_panduan_aktif_atau_mahasiswa_tanpa_dpa_ditolak(client, siap):
    r = ajukan(client, siap, headers=siap["h_mhs2"])  # prodi2 belum punya panduan aktif
    assert r.status_code == 409 and "panduan akademik aktif" in r.json()["detail"]

    b = client.get("/bimbingan", headers=siap["admin"], params={"aktif": True}).json()["data"][0]
    client.post(f"/bimbingan/{b['id']}/akhiri", json={}, headers=siap["h_kaprodi"])
    r = ajukan(client, siap)
    assert r.status_code == 409 and "pembimbing akademik" in r.json()["detail"]


def test_satu_pengajuan_terbuka_dan_cakupan_melihat(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    dua = ajukan(client, siap)
    assert dua.status_code == 409 and "menunggu keputusan" in dua.json()["detail"]
    # Mahasiswa lain dan dosen tak terkait: tidak melihat (404, bukan 403).
    assert client.get(f"/pengajuan/{pid}", headers=siap["h_mhs2"]).status_code == 404
    assert client.get("/pengajuan", headers=siap["h_mhs2"]).json()["total"] == 0
    for h in ("h_kaprodi", "h_kajur", "h_dekan"):
        assert client.get(f"/pengajuan/{pid}", headers=siap[h]).status_code == 200, h
    assert client.get(f"/pengajuan/{pid}", headers=siap["admin"]).status_code == 200


def test_audit_mencatat_pengajuan(client, siap, camunda):
    pid = ajukan(client, siap).json()["id"]
    camunda.worker_ekstraksi("inst-1")
    camunda.worker_rekomendasi("inst-1")
    camunda.dosen_putuskan("inst-1", "setuju")
    ambil(client, siap, pid)
    aksi = [x["aksi"] for x in client.get("/audit", headers=siap["admin"], params={"objek_id": pid}).json()["data"]]
    assert aksi == ["pengajuan.disetujui", "pengajuan.ajukan"]


# ====================================================================== mode lokal
def test_lokal_pipeline_berjalan_sendiri_sampai_tinjau(client, siap):
    r = ajukan(client, siap)
    assert r.status_code == 201 and r.json()["mode"] == "lokal"
    d = ambil(client, siap, r.json()["id"])
    assert d["tahap"] == "tinjau" and d["pesan_galat"] is None
    assert d["hasil_bacaan"]["ipk"] == 3.1 and d["rencana"]["rencana_mk"][0]["kode"] == "IF301"
    # Urutan langkah sama dengan BPMN, dan id_pengajuan diteruskan ke ekstraksi.
    urutan = [n for n, _ in siap["matkul"].panggilan]
    assert urutan == ["upload", "ekstraksi", "rekomendasi"]
    assert siap["matkul"].panggilan[1][1] == ("file_1", 3, r.json()["id"])


def test_lokal_keyakinan_rendah_menunggu_pemeriksaan(client, siap):
    siap["matkul"].keyakinan = 0.6
    pid = ajukan(client, siap).json()["id"]
    assert ambil(client, siap, pid)["tahap"] == "periksa"
    r = client.post(f"/pengajuan/{pid}/periksa", headers=siap["h_mhs"])
    assert r.status_code == 200
    assert ambil(client, siap, pid)["tahap"] == "tinjau"


def test_lokal_nim_tidak_cocok_tidak_menghalangi_rekomendasi(client, siap):
    siap["matkul"].nim_cocok = False
    pid = ajukan(client, siap).json()["id"]
    assert ambil(client, siap, pid)["tahap"] == "tinjau"
    assert "rekomendasi" in [n for n, _ in siap["matkul"].panggilan]


def test_lokal_dpa_memutuskan_revisi_lalu_setuju(client, siap):
    pid = ajukan(client, siap).json()["id"]
    url = f"/pengajuan/{pid}/keputusan"
    assert client.post(url, json={"keputusan": "setuju"}, headers=siap["h_mhs"]).status_code == 403
    assert client.post(url, json={"keputusan": "setuju"}, headers=siap["h_kaprodi"]).status_code == 403
    assert client.post(url, json={"keputusan": "revisi"}, headers=siap["h_dosen"]).status_code == 400  # catatan wajib
    assert client.post(url, json={"keputusan": "tolak"}, headers=siap["h_dosen"]).status_code == 422

    r = client.post(url, json={"keputusan": "revisi", "catatan": "Maksimal 18 SKS."}, headers=siap["h_dosen"])
    assert r.status_code == 200
    d = ambil(client, siap, pid)
    assert d["tahap"] == "tinjau" and d["jumlah_revisi"] == 1 and d["catatan_dpa"] == "Maksimal 18 SKS."
    assert d["rencana"]["rencana_mk"][0]["alasan"] == "uji Maksimal 18 SKS."
    assert siap["matkul"].panggilan[-1] == ("revisi", ("rnc_1", "Maksimal 18 SKS."))

    r = client.post(url, json={"keputusan": "setuju"}, headers=siap["h_dosen"])
    assert r.json()["status"] == "disetujui" and r.json()["tahap"] == "selesai"
    assert client.post(url, json={"keputusan": "setuju"}, headers=siap["h_dosen"]).status_code == 409


def test_lokal_keputusan_hanya_saat_tinjau(client, siap):
    siap["matkul"].keyakinan = 0.6
    pid = ajukan(client, siap).json()["id"]  # berhenti di periksa
    r = client.post(f"/pengajuan/{pid}/keputusan", json={"keputusan": "setuju"}, headers=siap["h_dosen"])
    assert r.status_code == 409 and "tidak sedang menunggu" in r.json()["detail"]


def test_lokal_langkah_gagal_menjadi_pesan_galat_lalu_bisa_dibatalkan(client, siap):
    siap["matkul"].gagal = {"ekstraksi"}
    pid = ajukan(client, siap).json()["id"]
    d = ambil(client, siap, pid)
    assert d["status"] == "diajukan" and d["tahap"] == "ekstraksi" and "ekstraksi gagal" in d["pesan_galat"]
    assert d["langkah"][0]["keadaan"] == "galat"
    assert client.post(f"/pengajuan/{pid}/batalkan", headers=siap["h_mhs"]).json()["status"] == "dibatalkan"
    siap["matkul"].gagal = set()
    assert ajukan(client, siap).status_code == 201


def test_lokal_dpa_berganti_pengajuan_ikut(client, siap, db, kampus):
    pid = ajukan(client, siap).json()["id"]
    pa2 = buat_orang_akun(db, "PA Dua", "pa2@k.ac.id")
    client.post("/penugasan", json={"orang_id": str(pa2.id), "peran": "dosen_pa", "unit_tipe": "prodi", "unit_id": kampus["prodi1"]["id"]}, headers=siap["admin"])
    r = client.post("/bimbingan/pindahkan", json={"dosen_asal_id": str(siap["orang"]["dosen"].id), "dosen_tujuan_id": str(pa2.id)}, headers=siap["h_kaprodi"])
    assert r.status_code == 200
    assert ambil(client, siap, pid, "admin")["dpa"]["nama_lengkap"] == "PA Dua"
    assert client.get("/pengajuan", headers=siap["h_dosen"]).json()["total"] == 0
    assert client.get("/pengajuan", headers=masuk(client, "pa2@k.ac.id")).json()["total"] == 1


def test_lokal_lulus_membatalkan_pengajuan_terbuka(client, siap):
    pid = ajukan(client, siap).json()["id"]
    k = client.get("/keanggotaan", headers=siap["admin"], params={"orang_id": str(siap["orang"]["mhs"].id), "aktif": True}).json()["data"][0]
    client.post(f"/keanggotaan/{k['id']}/status", json={"status": "lulus"}, headers=siap["h_kaprodi"])
    d = ambil(client, siap, pid, "admin")
    assert d["status"] == "dibatalkan" and "lulus" in d["catatan_dpa"]


# ====================================================================== klien
def test_klien_alurkerja_tanpa_tenant_dan_header_auth():
    dilihat = {}

    def h(req):
        dilihat["path"] = req.url.path
        dilihat["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"id": "x1"})

    klien = AlurKerjaKlien("https://a.test/", "user", "sandi", "kunci", http=httpx.Client(auth=("user", "sandi"), transport=httpx.MockTransport(h)))
    assert klien.mulai(business_key="p", variabel={"a": 1, "b": "x", "c": True, "d": 1.5, "e": None}) == "x1"
    assert dilihat["path"] == "/engine-rest/process-definition/key/kunci/start"
    assert dilihat["auth"].startswith("Basic ")


def test_klien_variabel_bertipe():
    ditangkap = {}

    def h(req):
        ditangkap["body"] = json.loads(req.content)
        return httpx.Response(200, json={"id": "x"})

    klien = AlurKerjaKlien("https://a.test", "u", "p", "k", http=httpx.Client(transport=httpx.MockTransport(h)))
    klien.mulai(business_key="p", variabel={"i": 3, "f": 1.5, "b": False, "s": "teks", "n": None})
    v = ditangkap["body"]["variables"]
    assert v["i"] == {"value": 3, "type": "Integer"} and v["f"] == {"value": 1.5, "type": "Double"}
    assert v["b"] == {"value": False, "type": "Boolean"} and v["s"] == {"value": "teks", "type": "String"}
    assert v["n"] == {"value": None, "type": "Null"}


# ====================================================================== ringkasan nilai untuk dasbor
def _ringkasan(client, d, who="h_mhs"):
    return client.get("/pengajuan/ringkasan-saya", headers=d[who])


def test_ringkasan_hanya_untuk_pemilik(client, siap):
    assert _ringkasan(client, siap).json() == {"ringkasan": None, "sumber": None}
    pid = ajukan(client, siap).json()["id"]
    r = _ringkasan(client, siap)
    assert r.status_code == 200, r.text
    assert r.json()["ringkasan"]["ipk"] == 3.1 and r.json()["sumber"]["pengajuan_id"] == pid
    # Pembimbing akademik tidak memperoleh daftar nilai lewat rute ini.
    assert _ringkasan(client, siap, "h_dosen").json()["ringkasan"] is None


def test_ringkasan_mengabaikan_batal_tapi_menerima_nim_demo_berbeda(client, siap):
    siap["matkul"].nim_cocok = False
    pid = ajukan(client, siap).json()["id"]
    ringkasan = _ringkasan(client, siap).json()
    assert ringkasan["ringkasan"]["ipk"] == 3.1
    assert ringkasan["sumber"]["pengajuan_id"] == pid
    client.post(f"/pengajuan/{pid}/batalkan", headers=siap["h_mhs"])
    siap["matkul"].panggilan.clear()
    siap["matkul"].nim_cocok = True
    pid = ajukan(client, siap).json()["id"]
    client.post(f"/pengajuan/{pid}/batalkan", headers=siap["h_mhs"])
    assert _ringkasan(client, siap).json()["ringkasan"] is None
    assert "ringkasan" not in [n for n, _ in siap["matkul"].panggilan]


def test_ringkasan_galat_matkul(client, siap):
    ajukan(client, siap)
    siap["matkul"].gagal = {"ringkasan"}
    assert _ringkasan(client, siap).status_code == 502
