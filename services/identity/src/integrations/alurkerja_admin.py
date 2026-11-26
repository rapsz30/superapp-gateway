"""API admin AlurKerja: membuat akun pengguna dan memasukkannya ke workspace.

API ini tidak ada di dokumentasi publik; bentuknya diambil dari halaman Console AlurKerja, jadi bisa berubah saat
AlurKerja diperbarui. Masuk memakai klien layanan Keycloak (client credentials) yang diberi peran realm
`platform_owner`. Hak itu luas: simpan rahasianya hanya di `.env` identity.
"""

from __future__ import annotations

import ssl
from typing import Any

import httpx

from src.core.config import get_settings


class AdminGalat(Exception):
    """AlurKerja atau Keycloak tidak dapat dihubungi, atau menolak permintaan."""


class AkunSudahAda(Exception):
    """Email sudah punya akun di AlurKerja."""


class AdminKlien:
    def __init__(
        self, url: str, realm: str, client_id: str, client_secret: str, workspace_id: str,
        *, ca_bundle: str = "", http: httpx.Client | None = None,
    ) -> None:
        self.url = url.rstrip("/").removesuffix("/engine-rest")
        self.realm = realm
        self._kredensial = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
        self.workspace_id: Any = int(workspace_id) if workspace_id.isdigit() else workspace_id
        verify: Any = ssl.create_default_context(cafile=ca_bundle) if ca_bundle else True
        self.http = http or httpx.Client(timeout=30.0, verify=verify)
        self._token = ""

    def _kirim(self, url: str, **kw: Any) -> httpx.Response:
        try:
            return self.http.post(url, **kw)
        except httpx.HTTPError as exc:
            raise AdminGalat(f"AlurKerja tidak dapat dihubungi: {type(exc).__name__}") from exc

    def masuk(self) -> str:
        r = self._kirim(f"{self.url}/sso/realms/{self.realm}/protocol/openid-connect/token", data=self._kredensial)
        token = r.json().get("access_token") if r.status_code == 200 else None
        if not token:
            raise AdminGalat(f"Keycloak menolak klien layanan (HTTP {r.status_code}).")
        self._token = str(token)
        return self._token

    def daftar_workspace(self) -> list[dict[str, Any]]:
        """Workspace di instalasi ini (hanya membaca), untuk mengisi ALURKERJA_WORKSPACE_ID."""
        token = self._token or self.masuk()
        try:
            r = self.http.get(
                f"{self.url}/api/v1/tenant/admin/workspaces", headers={"Authorization": f"Bearer {token}"})
        except httpx.HTTPError as exc:
            raise AdminGalat(f"AlurKerja tidak dapat dihubungi: {type(exc).__name__}") from exc
        if r.status_code != 200:
            raise AdminGalat(f"AlurKerja menolak membaca workspace (HTTP {r.status_code}): {r.text[:200]}")
        data: Any = r.json()
        while isinstance(data, dict):  # daftar bisa terbungkus data/content/items
            data = next((data[k] for k in ("data", "content", "items", "workspaces") if k in data), [])
        return [x for x in data if isinstance(x, dict)]

    def buat_pengguna(self, nama: str, email: str) -> bool:
        """Buat akun sebagai anggota workspace. True bila email pengaturan sandi terkirim."""
        isi = {"name": nama, "email": email, "workspace_id": self.workspace_id, "role": "member"}
        for percobaan in (1, 2):
            token = self._token or self.masuk()
            r = self._kirim(
                f"{self.url}/api/v1/tenant/admin/users", json=isi, headers={"Authorization": f"Bearer {token}"}
            )
            if r.status_code == 401 and percobaan == 1:  # token kedaluwarsa
                self._token = ""
                continue
            break
        if r.status_code == 409:
            raise AkunSudahAda(email)
        if r.status_code not in (200, 201):
            raise AdminGalat(f"AlurKerja menolak membuat akun (HTTP {r.status_code}): {r.text[:200]}")
        badan = r.json() if r.content else {}
        data = badan.get("data") if isinstance(badan.get("data"), dict) else badan
        return bool(data.get("password_email_sent"))


def dapatkan_admin() -> AdminKlien | None:
    """Klien admin bila dikonfigurasi lengkap; None berarti sinkron akun nonaktif."""
    s = get_settings()
    if not (s.alurkerja_url and s.alurkerja_admin_client_id and s.alurkerja_admin_client_secret
            and s.alurkerja_workspace_id):
        return None
    return AdminKlien(
        s.alurkerja_url, s.alurkerja_keycloak_realm, s.alurkerja_admin_client_id, s.alurkerja_admin_client_secret,
        s.alurkerja_workspace_id, ca_bundle=s.alurkerja_ca_bundle,
    )
