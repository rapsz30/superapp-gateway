"""Klien AlurKerja (Camunda 7) lewat REST `/engine-rest` dengan Basic Auth.

Proses: `perencanaan-studi-superapp` (alurkerja/perencanaan-studi-superapp.bpmn). Langkah AI dikerjakan worker
(alurkerja-connector/); identity memulai proses, menyelesaikan tugas mahasiswa dan tugas tinjauan dosen (dari
layar aplikasi), membaca keadaan, membatalkan, dan mengganti penerima tugas dosen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.core.config import get_settings


# Memulai proses dan menyelesaikan tugas menunggu listener notifikasi AlurKerja, yang di server bisa lebih
# dari 20 detik. Bila identity menyerah lebih dulu, prosesnya tetap terbuat di AlurKerja dan menjadi yatim.
BATAS_TULIS = 50.0


class AlurKerjaGalat(Exception):
    """AlurKerja tidak dapat dihubungi atau menolak permintaan."""


@dataclass
class Snapshot:
    """Keadaan sebuah instans proses pada saat dibaca."""

    state: str  # ACTIVE, COMPLETED, EXTERNALLY_TERMINATED, INTERNALLY_TERMINATED, atau HILANG
    aktif: list[str] = field(default_factory=list)  # id aktivitas yang sedang berjalan
    variabel: dict[str, Any] = field(default_factory=dict)
    galat: str | None = None  # pesan insiden (mis. langkah AI gagal) bila ada

    @property
    def selesai(self) -> bool:
        return self.state != "ACTIVE"


def _bertipe(nilai: Any) -> dict[str, Any]:
    if nilai is None:
        return {"value": None, "type": "Null"}
    if isinstance(nilai, bool):
        return {"value": nilai, "type": "Boolean"}
    if isinstance(nilai, int):
        return {"value": nilai, "type": "Integer"}
    if isinstance(nilai, float):
        return {"value": nilai, "type": "Double"}
    return {"value": str(nilai), "type": "String"}


def _nilai(item: dict[str, Any]) -> Any:
    """Nilai variabel riwayat. Tipe Json/Object yang dikirim sebagai string tetap string."""
    return item.get("value")


class AlurKerjaKlien:
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        process_key: str,
        tenant_id: str = "",
        http: httpx.Client | None = None,
        ca_bundle: str = "",
    ) -> None:
        self.url = url.rstrip("/")
        self.username = username
        self.process_key = process_key
        self.tenant_id = tenant_id
        self.http = http or httpx.Client(auth=(username, password), timeout=15.0, verify=ca_bundle or True)

    def _kirim(self, metode: str, jalur: str, **kw) -> httpx.Response:
        if metode != "GET":
            kw.setdefault("timeout", BATAS_TULIS)
        try:
            return self.http.request(metode, f"{self.url}/engine-rest{jalur}", **kw)
        except httpx.HTTPError as exc:
            raise AlurKerjaGalat(f"AlurKerja tidak dapat dihubungi: {type(exc).__name__}") from exc

    def pengguna_ada(self, email: str) -> bool:
        """Apakah email ini sudah menjadi pengguna di engine (syarat tugasnya tampil di Tasklist)."""
        r = self._kirim("GET", "/user", params={"id": email})
        if r.status_code != 200:
            raise AlurKerjaGalat(f"AlurKerja menolak membaca pengguna (HTTP {r.status_code}).")
        return bool(r.json())

    # ------------------------------------------------------------------ memulai
    def mulai(self, *, business_key: str, variabel: dict[str, Any]) -> str:
        """Mulai proses dari awal. Mengembalikan id instans."""
        jalur = f"/process-definition/key/{self.process_key}"
        if self.tenant_id:
            jalur += f"/tenant-id/{self.tenant_id}"
        r = self._kirim(
            "POST",
            jalur + "/start",
            json={"businessKey": business_key, "variables": {k: _bertipe(v) for k, v in variabel.items()}},
        )
        if r.status_code not in (200, 201):
            raise AlurKerjaGalat(f"AlurKerja menolak memulai proses (HTTP {r.status_code}).")
        instance_id = str(r.json().get("id") or "")
        if not instance_id:
            raise AlurKerjaGalat("AlurKerja tidak mengembalikan id proses.")
        return instance_id

    # ------------------------------------------------------------------ tugas manusia
    def _tugas(self, instance_id: str, task_key: str) -> list[dict[str, Any]]:
        r = self._kirim("GET", "/task", params={"processInstanceId": instance_id, "taskDefinitionKey": task_key})
        if r.status_code != 200:
            raise AlurKerjaGalat(f"Tugas proses tidak terbaca (HTTP {r.status_code}).")
        return r.json()

    def selesaikan_tugas(self, instance_id: str, task_key: str, variabel: dict[str, Any] | None = None) -> bool:
        """Selesaikan tugas manusia (Task_Unggah, Task_Periksa, Task_Tinjau) atas nama pemiliknya.

        False bila tugas tidak (lagi) ada, misalnya sudah diselesaikan permintaan sebelumnya.
        """
        tugas = self._tugas(instance_id, task_key)
        if not tugas:
            return False
        r = self._kirim(
            "POST",
            f"/task/{tugas[0]['id']}/complete",
            json={"variables": {k: _bertipe(v) for k, v in (variabel or {}).items()}},
        )
        if r.status_code not in (200, 204):
            raise AlurKerjaGalat(f"AlurKerja menolak menyelesaikan tugas (HTTP {r.status_code}).")
        return True

    def ganti_penerima(
        self, instance_id: str, email: str, task_key: str = "Task_Tinjau", variabel: str = "dosen_pa"
    ) -> int:
        """Ganti dosen untuk proses ini: variabel `dosen_pa` (dipakai tugas tinjauan berikutnya, mis. setelah
        revisi) dan tugas tinjauan yang sedang terbuka. Mengembalikan jumlah tugas terbuka yang dipindah."""
        v = self._kirim(
            "PUT",
            f"/process-instance/{instance_id}/variables/{variabel}",
            json=_bertipe(email.strip().lower()),
        )
        if v.status_code not in (200, 204):
            raise AlurKerjaGalat(f"Variabel {variabel} gagal diganti (HTTP {v.status_code}).")
        dipindah = 0
        for tugas in self._tugas(instance_id, task_key):
            a = self._kirim("POST", f"/task/{tugas['id']}/assignee", json={"userId": email.strip().lower()})
            if a.status_code not in (200, 204):
                raise AlurKerjaGalat(f"Penerima tugas gagal diganti (HTTP {a.status_code}).")
            dipindah += 1
        return dipindah

    # ------------------------------------------------------------------ membaca keadaan
    def snapshot(self, instance_id: str) -> Snapshot:
        r = self._kirim("GET", f"/history/process-instance/{instance_id}")
        if r.status_code == 404:
            return Snapshot(state="HILANG")
        if r.status_code != 200:
            raise AlurKerjaGalat(f"Status proses tidak terbaca (HTTP {r.status_code}).")
        state = str(r.json().get("state") or "")

        a = self._kirim(
            "GET", "/history/activity-instance", params={"processInstanceId": instance_id, "unfinished": "true"}
        )
        if a.status_code != 200:
            raise AlurKerjaGalat(f"Aktivitas proses tidak terbaca (HTTP {a.status_code}).")
        aktif = [str(x["activityId"]) for x in a.json() if x.get("activityId")]

        v = self._kirim(
            "GET", "/history/variable-instance", params={"processInstanceId": instance_id, "deserializeValues": "false"}
        )
        if v.status_code != 200:
            raise AlurKerjaGalat(f"Variabel proses tidak terbaca (HTTP {v.status_code}).")
        variabel = {x["name"]: _nilai(x) for x in v.json() if "name" in x}

        galat = None
        if state == "ACTIVE":
            i = self._kirim("GET", "/incident", params={"processInstanceId": instance_id})
            if i.status_code == 200 and i.json():
                galat = str(i.json()[0].get("incidentMessage") or "Langkah proses gagal.")
        return Snapshot(state=state, aktif=aktif, variabel=variabel, galat=galat)

    # ------------------------------------------------------------------ menghentikan
    def batalkan(self, instance_id: str) -> None:
        r = self._kirim(
            "DELETE", f"/process-instance/{instance_id}", params={"skipCustomListeners": "true"}
        )
        if r.status_code not in (200, 204, 404):  # 404: sudah tidak ada
            raise AlurKerjaGalat(f"AlurKerja menolak membatalkan proses (HTTP {r.status_code}).")


def json_atau_nilai(nilai: Any) -> Any:
    """Variabel daftar/objek dikirim worker sebagai String berisi JSON; kembalikan bentuk aslinya bila bisa."""
    if isinstance(nilai, str) and nilai[:1] in ("[", "{"):
        try:
            return json.loads(nilai)
        except ValueError:
            return nilai
    return nilai


def dapatkan_klien(process_key: str = "") -> AlurKerjaKlien | None:
    """Klien AlurKerja bila dikonfigurasi lengkap; None berarti mode lokal."""
    s = get_settings()
    if not (s.alurkerja_url and s.alurkerja_username and s.alurkerja_password):
        return None
    return AlurKerjaKlien(
        s.alurkerja_url,
        s.alurkerja_username,
        s.alurkerja_password,
        process_key or s.alurkerja_process_key,
        s.alurkerja_tenant_id,
        ca_bundle=s.alurkerja_ca_bundle,
    )
