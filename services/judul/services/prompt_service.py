class PromptService:
    """
    Service untuk handel prompt engineering
    """

    @staticmethod
    def create_recommendation_prompt(interests: str) -> str:

        return f"""
            Anda adalah dosen pembimbing informatika. Berikan 3 rekomendasi tugas akhir untuk mahasiswa S1.

            Minat: "{interests}"

            Untuk setiap rekomendasi, berikan:
            1. judul: Judul spesifik dengan teknologi yang jelas
            2. deskripsi: 2-3 kalimat tentang masalah, solusi, dan output
            3. metodologi: Tahapan penelitian dengan format:
            - Tahap 1: Literature Review (2 minggu) - aktivitas dan tools
            - Tahap 2: Persiapan Data (2 minggu) - aktivitas dan tools  
            - Tahap 3: Development (4 minggu) - teknologi yang digunakan
            - Tahap 4: Testing (2 minggu) - metode testing
            - Tahap 5: Dokumentasi (1 minggu)
            Setiap tahap harus spesifik dengan tools konkret (Python, TensorFlow, dll)
            4. keywords: 3-5 keywords bahasa Inggris untuk search paper

            Rules:
            - Metodologi harus actionable dan spesifik
            - Teknologi harus feasible untuk S1
            - Total durasi 4-6 bulan

            Output HANYA JSON dengan format:
            {{
            "rekomendasi": [
                {{
                "judul": "...",
                "deskripsi": "...",
                "metodologi": "...",
                "keywords": ["keyword1", "keyword2", "keyword3"]
                }}
            ]
            }}

            Gunakan bahasa Indonesia kecuali keywords (Inggris).
            """

    @staticmethod
    def create_validation_prompt(title: str) -> str:
        return f"Validasi Kelayakan judul TA ini: {title}"


prompt_service = PromptService()
