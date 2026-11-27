"""Klien layanan rekomendasi judul (jaringan internal)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

import httpx

from src.core.config import get_settings


class JudulGalat(Exception):
    """Layanan judul tidak dapat dihubungi atau gagal menyusun rekomendasi."""


_akun: ContextVar[str | None] = ContextVar("akun_judul", default=None)


@contextmanager
def atas_nama(akun_id: object) -> Iterator[None]:
    """Panggilan di dalam blok ini dicatat sebagai pemakaian AI milik akun tersebut."""
    tanda = _akun.set(str(akun_id))
    try:
        yield
    finally:
        _akun.reset(tanda)


class JudulKlien:
    def __init__(self, url: str, http: httpx.Client | None = None) -> None:
        self.url = url.rstrip("/")
        self.http = http or httpx.Client(timeout=55.0)  # di bawah batas 60 detik gateway

    def _kirim(self, jalur: str, isi: dict[str, Any]) -> dict[str, Any]:
        akun = _akun.get()
        try:
            r = self.http.post(f"{self.url}{jalur}", json=isi, headers={"X-User-Id": akun} if akun else {})
        except httpx.HTTPError as exc:
            raise JudulGalat(f"Layanan judul tidak dapat dihubungi: {type(exc).__name__}") from exc
        if r.status_code != 200:
            raise JudulGalat(f"Layanan judul menolak permintaan (HTTP {r.status_code}).")
        return r.json()

    def balas(
        self, pesan: list[dict], prodi: str, mata_kuliah: list[str], tema: list[str], kandidat: dict | None = None
    ) -> dict[str, Any]:
        hasil = self._kirim(
            "/chat", {"pesan": pesan, "prodi": prodi, "mata_kuliah": mata_kuliah, "tema": tema, "kandidat": kandidat}
        )
        if not str(hasil.get("balasan") or "").strip():
            raise JudulGalat("Layanan judul tidak mengembalikan balasan.")
        return hasil

    def rekomendasi(
        self, minat: str, prodi: str, mata_kuliah: list[str], tema: list[str], diskusi: str = ""
    ) -> list[dict[str, Any]]:
        hasil = self._kirim(
            "/get-recommendations",
            {"interests": minat, "prodi": prodi, "mata_kuliah": mata_kuliah, "tema": tema, "diskusi": diskusi},
        ).get("rekomendasi")
        if not isinstance(hasil, list) or not hasil:
            raise JudulGalat("Layanan judul tidak mengembalikan rekomendasi.")
        return hasil


def dapatkan_judul() -> JudulKlien:
    return JudulKlien(get_settings().judul_url)
