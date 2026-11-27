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
    # Rahasia khusus untuk mencatat pemakaian AI (matkul, judul, micro-credential). Sengaja terpisah dari
    # INTERNAL_TOKEN: pemegangnya hanya bisa menambah catatan. Kosong = pencatatan nonaktif.
    ai_catat_token: str = ""
    # Harga per satu juta token (USD) untuk perkiraan biaya. Kosong = biaya tidak ditampilkan.
    ai_harga_masuk_per_juta: str = ""
    ai_harga_keluar_per_juta: str = ""
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
    # Dashboard kaprodi di web: cerminan satu dashboard Analytics. Aktif bila slug, client id, client secret,
    # dan id dashboard terisi. Auth Token dibuat di Studio > Integration > Auth Token.
    alurkerja_auth_token_slug: str = ""
    alurkerja_client_id: str = ""
    alurkerja_client_secret: str = ""
    # Satu dashboard per tab halaman Analitik. Id kosong = tab itu belum aktif.
    alurkerja_dashboard_ringkasan: str = ""
    alurkerja_dashboard_matkul: str = ""
    alurkerja_dashboard_judul: str = ""
    alurkerja_report_tenant: str = "1"
    alurkerja_workspace: str = "studentgateway"
    alurkerja_env: str = "LIVE"
    # Pengajuan judul tugas akhir: layanan rekomendasi judul dan proses AlurKerja-nya.
    judul_url: str = "http://judul-api:8001"
    alurkerja_process_key_judul: str = "pengajuan-judul-superapp"
    # Sinkron akun dosen ke AlurKerja. Aktif bila klien layanan Keycloak (peran realm platform_owner) dan
    # id workspace terisi.
    alurkerja_admin_client_id: str = ""
    alurkerja_admin_client_secret: str = ""
    alurkerja_workspace_id: str = ""
    alurkerja_keycloak_realm: str = "alurkerja"
    alurkerja_sinkron_detik: int = 60
    # Biaya bcrypt. Jangan diturunkan di produksi; nilai kecil hanya untuk uji otomatis.
    bcrypt_rounds: int = 12
    # Registrasi publik ke prodi dummy. PRODI_TERBUKA kosong mematikan registrasi, batch dummy, dan panduan pribadi.
    registrasi_aktif: bool = False
    prodi_terbuka: str = ""
    registrasi_maks_per_jam: int = 100
    dummy_maks_sekali: int = 300

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
