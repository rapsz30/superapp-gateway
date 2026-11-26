"""Daftar tema tugas akhir yang baku, supaya judul dapat direkap per program studi.

Teks bebas akan memecah rekap ("AI", "Kecerdasan Buatan", "ML"), karena itu AI dan mahasiswa memilih dari daftar ini.
Mengubah daftar ini tidak mengubah tema pada pengajuan yang sudah tersimpan.
"""

LAINNYA = "Lainnya"

TEMA_JUDUL: tuple[str, ...] = (
    "Kecerdasan Buatan & Machine Learning",
    "Data Science & Analitik",
    "Visi Komputer & Pengolahan Citra",
    "Keamanan Siber",
    "Jaringan & Komputasi Awan",
    "Internet of Things & Sistem Tertanam",
    "Rekayasa Perangkat Lunak",
    "Pengembangan Web & Mobile",
    "Sistem Informasi & Tata Kelola",
    "Interaksi Manusia dan Komputer",
    "Multimedia & Gim",
    LAINNYA,
)

_PETA = {t.casefold(): t for t in TEMA_JUDUL}


def bakukan(tema: object) -> str:
    """Nama baku untuk tema keluaran AI; yang tidak dikenal menjadi "Lainnya"."""
    return _PETA.get(" ".join(str(tema or "").split()).casefold(), LAINNYA)
