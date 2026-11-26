"""Judul tugas akhir: pembimbing TA, rekomendasi, dan pengajuan lewat AlurKerja (ditiru) serta mode lokal."""

import json
import re

import httpx
import pytest

from src.integrations import alurkerja, judul as layanan_judul
from src.integrations.alurkerja import AlurKerjaKlien
from src.integrations.judul import JudulGalat
from tests.test_hak_akses import siapkan_dunia

ISI = {
    "topik": "keamanan jaringan",
    "tema": "Keamanan Siber",
    "judul": "Deteksi Serangan DDoS dengan Machine Learning",
    "deskripsi": "Membangun model deteksi serangan <DDoS> pada trafik HTTP.",
    "metodologi": "- Studi literatur\n- Eksperimen",
    "keywords": ["ddos"],
    "referensi": [{"sitasi": "Penulis (2024). Judul.", "link": "https://doi.org/10.1/x"}],
}


class Camunda:
    def __init__(self):
        self.proses: dict[str, dict] = {}
        self.mati = False

    def handler(self, req: httpx.Request) -> httpx.Response:
        if self.mati:
            raise httpx.ConnectError("mati", request=req)
        path = req.url.path.removeprefix("/engine-rest")
        body = json.loads(req.content) if req.content else None
        q = req.url.params
        if path == "/process-definition/key/pengajuan-judul-superapp/tenant-id/t1/start":
            iid = f"j-{len(self.proses) + 1}"
            v = {k: x["value"] for k, x in body["variables"].items()}
            self.proses[iid] = {"state": "ACTIVE", "vars": v, "aktif": "Task_TinjauJudul", "penerima": v["pembimbing"]}
            return httpx.Response(200, json={"id": iid})
        if m := re.fullmatch(r"/history/process-instance/(.+)", path):
            return httpx.Response(200, json={"state": self.proses[m[1]]["state"]})
        if path == "/history/activity-instance":
            a = self.proses[q["processInstanceId"]]["aktif"]
            return httpx.Response(200, json=[{"activityId": a}] if a else [])
        if path == "/history/variable-instance":
            v = self.proses[q["processInstanceId"]]["vars"]
            return httpx.Response(200, json=[{"name": k, "value": x} for k, x in v.items()])
        if path == "/incident":
            return httpx.Response(200, json=[])
        if m := re.fullmatch(r"/process-instance/([^/]+)/variables/(.+)", path):
            self.proses[m[1]]["vars"][m[2]] = body["value"]
            return httpx.Response(204)
        if m := re.fullmatch(r"/process-instance/(.+)", path):
            self.proses[m[1]].update(state="EXTERNALLY_TERMINATED", aktif=None)
            return httpx.Response(204)
        if path == "/task":
            p = self.proses[q["processInstanceId"]]
            ada = p["aktif"] == q["taskDefinitionKey"]
            return httpx.Response(200, json=[{"id": f"{q['processInstanceId']}|{p['aktif']}"}] if ada else [])
        if m := re.fullmatch(r"/task/(.+)\|(.+)/complete", path):
            self.putus(m[1], {k: x["value"] for k, x in body["variables"].items()})
            return httpx.Response(204)
        if m := re.fullmatch(r"/task/(.+)\|(.+)/assignee", path):
            self.proses[m[1]]["penerima"] = body["userId"]
            return httpx.Response(204)
        return httpx.Response(404, json={})

    def putus(self, iid, variabel):
        p = self.proses[iid]
        p["vars"].update(variabel)
        if p["aktif"] == "Task_PerbaikiJudul":
            p["aktif"] = "Task_TinjauJudul"
        elif p["vars"]["keputusan"] == "setuju":
            p.update(state="COMPLETED", aktif=None)
        else:
            p["aktif"] = "Task_PerbaikiJudul"


class JudulPalsu:
    def __init__(self):
        self.panggilan = []
        self.gagal = False

    def rekomendasi(self, minat, prodi, mata_kuliah, tema):
        if self.gagal:
            raise JudulGalat("mati")
        self.panggilan.append((minat, prodi, mata_kuliah, tema))
        dasar = {"deskripsi": "D", "metodologi": "M", "keywords": [], "referensi": []}
        return [{**dasar, "judul": "J1", "tema": "keamanan siber"}, {**dasar, "judul": "J2", "tema": "Ngawur"}]


@pytest.fixture
def dunia(client, db, admin, kampus, monkeypatch):
    d = siapkan_dunia(client, db, admin, kampus)
    d["admin"], d["prodi"], d["prodi2"] = admin, kampus["prodi1"]["id"], kampus["prodi2"]["id"]
    d["layanan"] = JudulPalsu()
    monkeypatch.setattr(layanan_judul, "dapatkan_judul", lambda: d["layanan"])
    return d


@pytest.fixture
def camunda(monkeypatch):
    c = Camunda()

    def klien(kunci=""):
        return AlurKerjaKlien(
            "https://alurkerja.test", "svc", "p", kunci or "x", tenant_id="t1",
            http=httpx.Client(transport=httpx.MockTransport(c.handler)),
        )

    monkeypatch.setattr(alurkerja, "dapatkan_klien", klien)
    return c


def tunjuk(client, d, dosen="dosen", who="h_kaprodi"):
    return client.put(
        "/pembimbing-ta",
        json={"mahasiswa_id": str(d["orang"]["mhs"].id), "dosen_id": str(d["orang"][dosen].id)},
        headers=d[who],
    )


def ajukan(client, d, **ubah):
    return client.post("/pengajuan-judul", json={**ISI, **ubah}, headers=d["h_mhs"])


def putus(client, d, pid, keputusan, catatan=None, who="h_dosen"):
    return client.post(f"/pengajuan-judul/{pid}/keputusan", json={"keputusan": keputusan, "catatan": catatan}, headers=d[who])


# ---------------------------------------------------------------- pembimbing TA
def test_hanya_kaprodi_prodinya_yang_menunjuk(client, dunia):
    assert tunjuk(client, dunia, who="h_dosen").status_code == 403
    assert tunjuk(client, dunia, who="h_mhs").status_code == 403
    assert tunjuk(client, dunia, dosen="mhs2").status_code == 400
    assert tunjuk(client, dunia).status_code == 200
    r = client.get(f"/pembimbing-ta?prodi_id={dunia['prodi']}", headers=dunia["h_kaprodi"])
    baris = {x["mahasiswa"]["nama_lengkap"]: x for x in r.json()["data"]}
    assert baris["Mahasiswa Satu"]["pembimbing"]["nama_lengkap"] == "Dosen PA"
    assert "Mahasiswa Dua" not in baris
    nama = [x["nama_lengkap"] for x in client.get(
        f"/pembimbing-ta/dosen?prodi_id={dunia['prodi']}", headers=dunia["h_kaprodi"]).json()["data"]]
    assert "Dosen PA" in nama and "Kaprodi" in nama and "Mahasiswa Dua" not in nama


# ---------------------------------------------------------------- rekomendasi
def test_rekomendasi_memakai_prodi_dan_disimpan(client, dunia):
    r = client.post("/judul/rekomendasi", json={"minat": "keamanan"}, headers=dunia["h_mhs"])
    assert r.status_code == 200, r.text
    assert dunia["layanan"].panggilan[0][1]  # nama prodi dikirim
    assert "Keamanan Siber" in dunia["layanan"].panggilan[0][3]
    assert [x["tema"] for x in r.json()["rekomendasi"]] == ["Keamanan Siber", "Lainnya"]
    assert client.get("/judul/saya", headers=dunia["h_mhs"]).json()["riwayat"][0]["topik"] == "keamanan"
    assert client.post("/judul/rekomendasi", json={"minat": "x" * 301}, headers=dunia["h_mhs"]).status_code == 422
    assert client.post("/judul/rekomendasi", json={"minat": "keamanan"}, headers=dunia["h_dosen"]).status_code == 403
    dunia["layanan"].gagal = True
    assert client.post("/judul/rekomendasi", json={"minat": "keamanan"}, headers=dunia["h_mhs"]).status_code == 502


# ---------------------------------------------------------------- pengajuan
def test_mahasiswa_memilih_pembimbing_saat_pengajuan(client, dunia, camunda):
    assert ajukan(client, dunia).status_code == 409
    daftar = client.get("/judul/pembimbing", headers=dunia["h_mhs"]).json()["data"]
    dosen = next(item for item in daftar if item["nama_lengkap"] == "Dosen PA")
    assert ajukan(client, dunia, pembimbing_id=dosen["id"]).status_code == 201
    assert camunda.proses["j-1"]["penerima"] == "dosen@k.ac.id"


def test_alur_alurkerja_revisi_lalu_setuju(client, dunia, camunda):
    tunjuk(client, dunia)
    r = ajukan(client, dunia)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    v = camunda.proses["j-1"]["vars"]
    assert v["tema"] == "Keamanan Siber"
    assert v["pembimbing"] == "dosen@k.ac.id" and v["initiator"] == "svc" and v["nim_mahasiswa"] == "20110001"
    assert "&lt;DDoS&gt;" in v["ringkasan_judul"] and "Mahasiswa Satu" not in json.dumps(v)
    assert ajukan(client, dunia).status_code == 409  # satu pengajuan terbuka

    assert putus(client, dunia, pid, "revisi").status_code == 400
    assert putus(client, dunia, pid, "setuju", who="h_mhs").status_code == 403
    # Dosen memutuskan di Tasklist: aplikasi membacanya saat dibuka.
    camunda.putus("j-1", {"keputusan": "revisi", "catatan_dosen": "Persempit objeknya."})
    p = client.get("/judul/saya", headers=dunia["h_mhs"]).json()["pengajuan"]
    assert p["tahap"] == "perbaikan" and p["catatan"] == "Persempit objeknya."

    baru = {**ISI, "judul": "Deteksi DDoS pada Server Kampus"}
    r = client.put(f"/pengajuan-judul/{pid}", json=baru, headers=dunia["h_mhs"])
    assert r.status_code == 200, r.text
    assert r.json()["tahap"] == "tinjau" and r.json()["jumlah_revisi"] == 1
    assert camunda.proses["j-1"]["aktif"] == "Task_TinjauJudul"
    assert "Revisi ke-1" in camunda.proses["j-1"]["vars"]["ringkasan_judul"]
    assert client.put(f"/pengajuan-judul/{pid}", json=baru, headers=dunia["h_mhs"]).status_code == 409

    r = putus(client, dunia, pid, "setuju")
    assert r.status_code == 200 and r.json()["status"] == "disetujui"
    assert camunda.proses["j-1"]["state"] == "COMPLETED"


def test_ganti_pembimbing_memindahkan_tugas(client, dunia, camunda):
    tunjuk(client, dunia)
    pid = ajukan(client, dunia).json()["id"]
    assert tunjuk(client, dunia, dosen="kaprodi").status_code == 200
    assert camunda.proses["j-1"]["penerima"] == "kaprodi@k.ac.id"
    assert camunda.proses["j-1"]["vars"]["pembimbing"] == "kaprodi@k.ac.id"
    assert putus(client, dunia, pid, "setuju").status_code in (403, 404)
    assert putus(client, dunia, pid, "setuju", who="h_kaprodi").status_code == 200


def test_batalkan_dan_alurkerja_mati(client, dunia, camunda):
    tunjuk(client, dunia)
    camunda.mati = True
    assert ajukan(client, dunia).status_code == 502
    camunda.mati = False
    pid = ajukan(client, dunia).json()["id"]  # kegagalan tadi tidak meninggalkan pengajuan terbuka
    r = client.post(f"/pengajuan-judul/{pid}/batalkan", headers=dunia["h_mhs"])
    assert r.status_code == 200 and r.json()["status"] == "dibatalkan"
    assert camunda.proses["j-1"]["state"] == "EXTERNALLY_TERMINATED"


def test_mode_lokal(client, dunia):
    tunjuk(client, dunia)
    pid = ajukan(client, dunia).json()["id"]
    assert putus(client, dunia, pid, "revisi", "Ganti").json()["tahap"] == "perbaikan"
    assert client.put(f"/pengajuan-judul/{pid}", json=ISI, headers=dunia["h_mhs"]).json()["tahap"] == "tinjau"
    assert putus(client, dunia, pid, "setuju").json()["status"] == "disetujui"
    daftar = client.get("/pengajuan-judul", headers=dunia["h_dosen"]).json()
    assert daftar["total"] == 1
    assert client.get("/pengajuan-judul", headers=dunia["h_mhs2"]).json()["total"] == 0


def test_tautan_referensi_harus_http(client, dunia):
    tunjuk(client, dunia)
    r = ajukan(client, dunia, referensi=[{"sitasi": "x", "link": "javascript:alert(1)"}])
    assert r.status_code == 422


# ---------------------------------------------------------------- tema
def test_tema_wajib_dari_daftar(client, dunia):
    tunjuk(client, dunia)
    assert ajukan(client, dunia, tema="Bebas").status_code == 422
    assert "Keamanan Siber" in client.get("/judul/tema", headers=dunia["h_mhs"]).json()["data"]


def test_statistik_tema_per_prodi(client, dunia):
    tunjuk(client, dunia)
    pid = ajukan(client, dunia).json()["id"]
    client.post(f"/pengajuan-judul/{pid}/batalkan", headers=dunia["h_mhs"])
    pid = ajukan(client, dunia, tema="Data Science & Analitik").json()["id"]

    def rekap(who, tambahan=""):
        return client.get(f"/judul/statistik-tema{tambahan}", headers=dunia[who])

    d = rekap("h_kaprodi").json()["data"]
    assert len(d) == 1 and d[0]["total"] == 1  # yang dibatalkan tidak dihitung
    assert d[0]["tema"] == [{"tema": "Data Science & Analitik", "disetujui": 0, "berjalan": 1, "total": 1}]
    putus(client, dunia, pid, "setuju")
    assert rekap("h_kaprodi").json()["data"][0]["tema"][0]["disetujui"] == 1
    assert "mhs" not in rekap("h_kaprodi").text and "Mahasiswa" not in rekap("h_kaprodi").text
    assert rekap("h_mhs").status_code == 403 and rekap("h_dosen").status_code == 403
    assert rekap("h_kaprodi", f"?prodi_id={dunia['prodi2']}").status_code == 403
