"""Klien API laporan AlurKerja (Analytics): susunan dashboard dan hasil tiap pertanyaan.

Dipakai agar halaman kaprodi mencerminkan dashboard yang disusun di Studio. Autentikasi memakai Auth Token
integrasi AlurKerja (Studio > Integration > Auth Token). API ini tidak ada di dokumentasi publik; bentuknya
diambil dari panggilan aplikasi AlurKerja sendiri, jadi bisa berubah saat AlurKerja diperbarui.
"""

from __future__ import annotations

import ssl
import time
from typing import Any

import httpx

from src.core.config import get_settings


class LaporanGalat(Exception):
    """API laporan tidak dapat dihubungi atau menolak permintaan."""


# Token disimpan per proses supaya tidak masuk ulang pada setiap permintaan.
_token: dict[str, tuple[str, float]] = {}


class LaporanKlien:
    def __init__(
        self,
        url: str,
        slug: str,
        client_id: str,
        client_secret: str,
        *,
        tenant: str,
        workspace: str,
        env: str,
        ca_bundle: str = "",
        http: httpx.Client | None = None,
    ) -> None:
        self.url = url.rstrip("/").removesuffix("/engine-rest")
        self.slug = slug
        self._kredensial = {"client_id": client_id, "client_secret": client_secret}
        self.dasar = f"/api/v1/report/{tenant}"
        self.header = {"X-ACTIVE-TENANT": workspace, "x-act-env": env}
        verify: Any = ssl.create_default_context(cafile=ca_bundle) if ca_bundle else True
        self.http = http or httpx.Client(timeout=30.0, verify=verify)

    def _kirim(self, metode: str, url: str, **kw: Any) -> httpx.Response:
        try:
            return self.http.request(metode, url, **kw)
        except httpx.HTTPError as exc:
            raise LaporanGalat(f"AlurKerja tidak dapat dihubungi: {type(exc).__name__}") from exc

    def _masuk(self) -> str:
        r = self._kirim("POST", f"{self.url}/api/v1/integration/auth_token/{self.slug}/login", json=self._kredensial)
        if r.status_code != 200:
            raise LaporanGalat(f"Auth Token ditolak AlurKerja (HTTP {r.status_code}).")
        badan = r.json()
        data = badan.get("data") or badan
        token = str(data.get("access_token") or "")
        if not token:
            raise LaporanGalat("AlurKerja tidak mengembalikan access_token.")
        _token[self.slug] = (token, time.monotonic() + max(60, int(data.get("expires_in") or 3600)) - 60)
        return token

    def _panggil(self, metode: str, jalur: str, **kw: Any) -> dict[str, Any]:
        tersimpan = _token.get(self.slug)
        token = tersimpan[0] if tersimpan and tersimpan[1] > time.monotonic() else self._masuk()
        for percobaan in (1, 2):
            r = self._kirim(
                metode, f"{self.url}{self.dasar}{jalur}", headers={**self.header, "Authorization": f"Bearer {token}"}, **kw
            )
            if r.status_code == 401 and percobaan == 1:  # token dicabut sebelum waktunya
                token = self._masuk()
                continue
            break
        if r.status_code != 200:
            raise LaporanGalat(f"API laporan menolak {metode} {jalur} (HTTP {r.status_code}).")
        return r.json()

    def dashboard(self, dashboard_id: str) -> dict[str, Any]:
        return self._panggil("GET", f"/dashboard/{dashboard_id}/app")

    def hasil(self, question_id: int) -> list[dict[str, Any]]:
        badan = self._panggil("POST", f"/question/{question_id}/execute-query", json={})
        if not badan.get("success"):
            raise LaporanGalat(f"Pertanyaan {question_id} gagal dijalankan.")
        return list((badan.get("data") or {}).get("results") or [])


def dapatkan_laporan() -> LaporanKlien | None:
    """Klien bila dikonfigurasi lengkap; None berarti dashboard web tidak diaktifkan."""
    s = get_settings()
    wajib = (s.alurkerja_url, s.alurkerja_auth_token_slug, s.alurkerja_client_id, s.alurkerja_client_secret)
    if not all(wajib):
        return None
    return LaporanKlien(
        s.alurkerja_url,
        s.alurkerja_auth_token_slug,
        s.alurkerja_client_id,
        s.alurkerja_client_secret,
        tenant=s.alurkerja_report_tenant,
        workspace=s.alurkerja_workspace,
        env=s.alurkerja_env,
        ca_bundle=s.alurkerja_ca_bundle,
    )
