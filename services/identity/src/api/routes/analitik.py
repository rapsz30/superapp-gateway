"""Dashboard kaprodi: cerminan dashboard Analytics AlurKerja (susunan dan angka diambil saat diminta).

Tiap tab halaman Analitik membaca satu dashboard di Studio.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter

from src.api.deps import Saya
from src.api.errors import dilarang, galat
from src.core.config import get_settings
from src.integrations import laporan
from src.integrations.laporan import LaporanGalat

router = APIRouter(tags=["analitik"])
log = logging.getLogger("identity.analitik")

MAKS_BARIS = 200
# Hanya pengaturan tampilan yang diteruskan. SQL pertanyaan tidak pernah dikirim ke browser.
KONFIGURASI = ("title", "header", "value_column", "x_axis", "y_axis", "colors", "legend")


def _kartu(klien: laporan.LaporanKlien, butir: dict[str, Any], pertanyaan: dict[Any, dict]) -> dict[str, Any]:
    q = pertanyaan.get(butir.get("question_id"))
    kartu: dict[str, Any] = {
        "id": str(butir.get("i") or butir.get("question_id")),
        "x": butir.get("x") or 0,
        "y": butir.get("y") or 0,
        "w": butir.get("w") or 6,
        "h": butir.get("h") or 4,
        "judul": (q or {}).get("title") or "",
        "jenis": (q or {}).get("visualization_type") or butir.get("type") or "",
        "konfigurasi": {k: v for k, v in ((q or {}).get("chart_config") or {}).items() if k in KONFIGURASI},
        "baris": [],
        "galat": None,
    }
    if q is None:
        kartu["galat"] = "Jenis kartu ini belum didukung di web. Buka di AlurKerja."
        return kartu
    try:
        kartu["baris"] = klien.hasil(q["id"])[:MAKS_BARIS]
    except LaporanGalat as exc:
        log.warning("Kartu analitik %s gagal: %s", q.get("id"), exc)
        kartu["galat"] = "Data kartu ini belum dapat dimuat."
    return kartu


@router.get("/analitik/dashboard")
def dashboard(saya: Saya, tab: Literal["ringkasan", "matkul", "judul"] = "ringkasan") -> dict:
    """Rekap seluruh prodi (tanpa identitas mahasiswa), untuk kaprodi dan superadmin."""
    if not (saya.superadmin or saya.cakupan.kaprodi_ids):
        raise dilarang("Dashboard hanya untuk kaprodi.")
    klien = laporan.dapatkan_laporan()
    dashboard_id = getattr(get_settings(), f"alurkerja_dashboard_{tab}")
    if klien is None or not dashboard_id:
        raise galat(503, "Dashboard AlurKerja belum dikonfigurasi.")
    try:
        d = klien.dashboard(dashboard_id)
    except LaporanGalat as exc:
        log.error("Dashboard AlurKerja gagal dimuat: %s", exc)
        raise galat(502, "Dashboard belum dapat dimuat dari AlurKerja. Coba lagi beberapa saat lagi.") from None

    pertanyaan = {q["id"]: q for q in d.get("questions") or []}
    butir = sorted(d.get("dashboard_items") or [], key=lambda b: (b.get("y") or 0, b.get("x") or 0))
    with ThreadPoolExecutor(max_workers=4) as pool:
        kartu = list(pool.map(lambda b: _kartu(klien, b, pertanyaan), butir))
    return {
        "judul": d.get("name") or "Dashboard",
        "deskripsi": d.get("description") or "",
        "diambil_pada": datetime.now(UTC).isoformat(),
        "kartu": kartu,
    }
