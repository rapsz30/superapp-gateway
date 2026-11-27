"""Fire-and-forget pemakaian AI ke identity; tidak pernah membawa prompt atau jawaban."""
from __future__ import annotations

import json
import threading
import urllib.request
from contextvars import ContextVar

from src.core.config import get_settings

akun_id_ai: ContextVar[str | None] = ContextVar("microcred_akun_id_ai", default=None)


def catat(model: str, masuk: int = 0, keluar: int = 0, durasi_ms: int = 0, berhasil: bool = True) -> None:
    s = get_settings()
    if not s.ai_catat_token:
        return
    body = json.dumps({"layanan": "microcred", "fitur": "nilai_esai", "model": model,
                       "token_masuk": masuk, "token_keluar": keluar, "durasi_ms": durasi_ms,
                       "berhasil": berhasil, "akun_id": akun_id_ai.get()}).encode()
    url = s.identity_url.rstrip("/") + "/internal/ai-pemakaian"

    def kirim() -> None:
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "X-AI-Token": s.ai_catat_token})
            with urllib.request.urlopen(req, timeout=3):
                pass
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Gagal mencatat pemakaian AI microcred: %s", type(e).__name__)

    threading.Thread(target=kirim, daemon=True).start()
