"""Pengirim pemakaian AI tanpa menunggu layanan identity."""
from __future__ import annotations

import json
import os
import threading
import urllib.request
from contextvars import ContextVar

akun_id: ContextVar[str | None] = ContextVar("judul_akun_id", default=None)


def catat(fitur: str, model: str, masuk: int = 0, keluar: int = 0, durasi_ms: int = 0, berhasil: bool = True) -> None:
    token = os.getenv("AI_CATAT_TOKEN", "")
    if not token:
        return
    data = json.dumps({"layanan": "judul", "fitur": fitur, "model": model, "token_masuk": masuk,
                       "token_keluar": keluar, "durasi_ms": durasi_ms, "berhasil": berhasil,
                       "akun_id": akun_id.get()}).encode()
    url = os.getenv("IDENTITY_URL", "http://identity-api:8002").rstrip("/") + "/internal/ai-pemakaian"

    def kirim() -> None:
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "X-AI-Token": token})
            with urllib.request.urlopen(req, timeout=3):
                pass
        except Exception as e:
            print(f"Gagal mencatat pemakaian AI judul: {type(e).__name__}")

    threading.Thread(target=kirim, daemon=True).start()
