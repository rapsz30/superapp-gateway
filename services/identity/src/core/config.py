"""Konfigurasi layanan identity. Semua nilai dibaca dari environment."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Nilai bawaan Micro-cred dan tebakan umum. Ditolak sebagai secret.
SECRET_TERLARANG = {"", "replace-with-secure-secret", "changeme", "secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://identity:identity@identity-db:5432/identity"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "superapp-identity"
    access_token_menit: int = 15
    refresh_token_hari: int = 7
    zona_waktu: str = "Asia/Jakarta"
    panduan_dir: str = "./data/panduan"
    panduan_maks_mb: int = 20
    # Batas percobaan login gagal per (email, alamat) dalam jendela waktu.
    login_maks_gagal: int = 5
    login_jendela_detik: int = 900
    # Rahasia bersama dengan verifier gateway untuk endpoint /internal. Kosong = endpoint nonaktif.
    internal_token: str = ""
    # Layanan matkul (langkah AI proses). Identity hanya menyimpan berkas KHS lewat endpoint upload-nya.
    matkul_url: str = "http://matkul:3000"
    matkul_service_token: str = ""
    # AlurKerja (Camunda REST). Bila url, username, dan password terisi, pengajuan berjalan lewat AlurKerja
    # dan DPA memutuskan di Tasklist. Bila kosong, mode lokal: DPA memutuskan lewat API identity.
    alurkerja_url: str = ""
    alurkerja_username: str = ""
    alurkerja_password: str = ""
    alurkerja_process_key: str = "perencanaan-studi-superapp"
    # Pengguna yang menjadi ${initiator} (penerima tugas mahasiswa di BPMN). Kosong = ALURKERJA_USERNAME.
    alurkerja_initiator: str = ""
    alurkerja_tenant_id: str = ""
    alurkerja_ca_bundle: str = ""
    # Biaya bcrypt. Jangan diturunkan di produksi; nilai kecil hanya untuk uji otomatis.
    bcrypt_rounds: int = 12

    @field_validator("jwt_secret")
    @classmethod
    def _secret_layak(cls, v: str) -> str:
        if v.strip() in SECRET_TERLARANG or len(v.strip()) < 32:
            raise ValueError(
                "JWT_SECRET wajib diisi dengan minimal 32 karakter dan bukan nilai bawaan."
            )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
