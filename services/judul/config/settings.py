# KONFIGURASI SISTEM

import os
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class Settings:
    """ Menyimpan konfigurasi aplikasi """

    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

    # API Configuration
    API_TITLE: str = "Chatbot Rekomendasi Judul Tugas Akhir"
    API_DECRIPTION: str = "API untuk mendapatkan rekomendasi judul tugas akhir menggunakan OpenAI."
    API_VERSION: str = "1.0.0"

    # CROS Settings
    CROS_ORIGINS: list = ["http://localhost:8501/"]

    # OpenAI Settings (sama bawaan dengan layanan matkul)
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-6-luna")
    IDENTITY_URL: str = os.getenv("IDENTITY_URL", "http://identity-api:8002")
    AI_CATAT_TOKEN: str = os.getenv("AI_CATAT_TOKEN", "")

    @staticmethod
    def opsi_model(model: str) -> dict:
        """Model gpt-5 ke atas hanya menerima temperature selain 1 bila reasoning_effort "none".
        Model lama menolak parameter itu."""
        if re.match(r"(gpt-([5-9]|\d{2})|o\d)", model):
            return {"extra_body": {"reasoning_effort": "none"}}
        return {}

    @staticmethod
    def get_openai_client():
        """Membuat klien OpenAI dengan batas waktu agar selesai sebelum batas gateway.

        Kunci kosong diganti penanda agar modul tetap bisa diimpor (sama seperti
        perilaku sebelumnya); pemanggilan API tetap gagal autentikasi sampai .env diisi.
        """
        try:
            kunci = Settings.OPENAI_API_KEY.strip() or "sk-not-configured"
            return OpenAI(api_key=kunci, timeout=35.0, max_retries=1)
        except Exception as e:
            print(f"Konfigurasi OpenAI Error : {e}")
            raise


# Create singleton settings instance
settings = Settings()
