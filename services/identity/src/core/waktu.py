"""Tanggal 'hari ini' mengikuti zona waktu kampus (WIB), bukan UTC."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.core.config import get_settings


def hari_ini() -> date:
    return datetime.now(ZoneInfo(get_settings().zona_waktu)).date()
