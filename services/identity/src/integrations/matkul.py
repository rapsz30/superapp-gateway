"""Klien layanan matkul (jaringan internal, token layanan).

Mode AlurKerja: identity hanya menyimpan berkas KHS (upload). Langkah AI dijalankan worker AlurKerja.
Mode lokal (tanpa AlurKerja): identity memanggil ketiga langkah itu sendiri dengan urutan yang sama seperti BPMN.
"""

from __future__ import annotations

from typing import Any

import httpx

from src.core.config import get_settings


class MatkulGalat(Exception):
    """Layanan matkul tidak dapat dihubungi atau menolak permintaan."""


class MatkulKlien:
    def __init__(self, url: str, token: str, http: httpx.Client | None = None) -> None:
        self.url = url.rstrip("/")
        # Ekstraksi dan rekomendasi memanggil LLM: beri waktu, tetapi tidak tanpa batas.
        self.http = http or httpx.Client(timeout=180.0)
        self.headers = {"Authorization": f"Bearer {token}"}

    def _panggil(self, jalur: str, **kw: Any) -> dict[str, Any]:
        try:
            r = self.http.post(f"{self.url}/api/matkul/{jalur}", headers=self.headers, **kw)
        except httpx.HTTPError as exc:
            raise MatkulGalat(f"Layanan matkul tidak dapat dihubungi: {type(exc).__name__}") from exc
        if r.status_code != 200:
            try:
                pesan = r.json().get("error")
            except ValueError:
                pesan = None
            raise MatkulGalat(pesan or f"Layanan matkul menolak permintaan (HTTP {r.status_code}).")
        return r.json()

    def upload(self, isi: bytes, nama_berkas: str) -> str:
        data = self._panggil("upload", files={"file": (nama_berkas, isi, "application/pdf")})
        khs_file_id = str(data.get("khs_file_id") or "")
        if not khs_file_id:
            raise MatkulGalat("Layanan matkul tidak mengembalikan id berkas.")
        return khs_file_id

    def ekstraksi(self, khs_file_id: str, semester_target: int, id_pengajuan: str) -> dict[str, Any]:
        return self._panggil(
            "extract-khs",
            json={"khs_file_id": khs_file_id, "semester_target": semester_target, "id_pengajuan": id_pengajuan},
        )

    def rekomendasi(self, khs_ref: str, semester_target: int) -> dict[str, Any]:
        return self._panggil("recommend", json={"khs_ref": khs_ref, "semester_target": semester_target})

    def revisi(self, rencana_ref: str, catatan_dosen: str) -> dict[str, Any]:
        return self._panggil("revise", json={"rencana_ref": rencana_ref, "catatan_dosen": catatan_dosen})


def dapatkan_matkul() -> MatkulKlien:
    s = get_settings()
    if not s.matkul_service_token:
        raise MatkulGalat("MATKUL_SERVICE_TOKEN belum diatur di layanan identity.")
    return MatkulKlien(s.matkul_url, s.matkul_service_token)
