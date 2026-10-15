# KONFIGURASI SISTEM

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class Settings:
    """ Menyimpan konfigurasi aplikasi """

    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

    # API Configuration
    API_TITLE: str = "Chatbot Rekomendasi Judul Tugas Akhir"
    API_DECRIPTION: str = "API untuk mendapatkan rekomendasi judul tugas akhir menggunakan Groq."
    API_VERSION: str = "1.0.0"

    # CROS Settings
    CROS_ORIGINS: list = ["http://localhost:8501/"]

    # Groq Settings
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    @staticmethod
    def get_groq_client():
        """ Membuat 
        """
        try:
            return Groq(api_key=Settings.GROQ_API_KEY)
        except Exception as e:
            print(f"Konfigurasi Groq Error : {e}")
            raise


# Create singleton settings instance
settings = Settings()
