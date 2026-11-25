"""Ekstraksi teks dari PDF panduan akademik (tanpa OCR)."""

from __future__ import annotations

import io
import re

from pypdf import PdfReader
from pypdf.errors import PyPdfError

# Batas yang disimpan. Layanan rekomendasi memotong lagi sesuai kebutuhan prompt.
MAKS_KARAKTER = 300_000
# Di bawah ini dianggap tidak berisi teks (umumnya PDF hasil scan).
MIN_KARAKTER = 200


class PdfTidakBisaDibaca(Exception):
    pass


def _rapikan(teks: str) -> str:
    teks = teks.replace("\r", "\n").replace("\x00", "")
    teks = re.sub(r"[ \t]+\n", "\n", teks)
    teks = re.sub(r"\n{3,}", "\n\n", teks)
    teks = re.sub(r"[ \t]{2,}", " ", teks)
    return teks.strip()


def ekstrak_teks(isi: bytes) -> str:
    """Kembalikan teks PDF yang sudah dirapikan.

    Lempar PdfTidakBisaDibaca bila berkas rusak, terkunci, atau hampir tanpa teks.
    """
    try:
        pembaca = PdfReader(io.BytesIO(isi))
        if pembaca.is_encrypted and not pembaca.decrypt(""):
            raise PdfTidakBisaDibaca("PDF terkunci dengan kata sandi.")
        bagian: list[str] = []
        total = 0
        for halaman in pembaca.pages:
            potongan = halaman.extract_text() or ""
            bagian.append(potongan)
            total += len(potongan)
            if total >= MAKS_KARAKTER:
                break
    except PdfTidakBisaDibaca:
        raise
    except (PyPdfError, ValueError, KeyError, OSError, RecursionError) as exc:
        raise PdfTidakBisaDibaca("PDF tidak dapat dibaca atau rusak.") from exc

    teks = _rapikan("\n".join(bagian))[:MAKS_KARAKTER]
    if len(teks) < MIN_KARAKTER:
        raise PdfTidakBisaDibaca(
            "PDF hampir tidak berisi teks (kemungkinan hasil scan atau gambar). "
            "Unggah PDF yang teksnya bisa dipilih."
        )
    return teks
