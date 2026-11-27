# INTERAKSI DENGAN LAYANAN AI

import json
from typing import Dict, Any
import time
from ai_usage import catat

from openai import APIConnectionError, BadRequestError

from config.settings import settings
from services.prompt_service import TEMA_BAWAAN, prompt_service
from services.reference_service import reference_service


MAKS_PERCOBAAN = 3


class AIService:
    """ Handle interaksi dengan AI """

    def __init__(self):
        self.client = settings.get_openai_client()
        self.model = settings.OPENAI_MODEL

    def get_recommendations(
        self, interests: str, prodi: str = "", mata_kuliah: list | None = None, tema: list | None = None,
        diskusi: str = "",
    ) -> Dict[str, Any]:
        # Validasi input
        if not interests or not interests.strip():
            raise ValueError("Interests tidak boleh kosong.")

        print("="*50)
        print("STEP 1: Generate Recommendation with AI... ")

        # Generate prompt
        prompt = prompt_service.create_recommendation_prompt(interests, prodi, mata_kuliah, tema, diskusi)

        # Model sesekali menghasilkan JSON yang ditolak atau tidak lengkap; ulangi sebelum menyerah.
        for percobaan in range(1, MAKS_PERCOBAAN + 1):
            try:
                recommendations = json.loads(self._call_openai_api(prompt))
                self._validate_response(recommendations)
                break
            except (APIConnectionError, BadRequestError, ValueError, TypeError) as e:
                print(f"Percobaan {percobaan} gagal: {type(e).__name__}")
                if percobaan == MAKS_PERCOBAAN:
                    raise RuntimeError("AI tidak menghasilkan rekomendasi yang sah.") from e
        self._rapikan(recommendations, tema or TEMA_BAWAAN)

        print("STEP 2: AI generated recommendations successfully.")
        print(
            f"Total Recommendations: {len(recommendations.get('rekomendasi', []))}")

        # Fetch real references
        print("STEP 3: Fetching real references from Semantic Scholar... ")
        recommendations_with_refs = self._add_real_references(recommendations)

        print("STEP 4: Process completed!")
        print("="*50)

        return recommendations_with_refs

    def _call_openai_api(self, prompt: str) -> str:
        mulai = time.monotonic()
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=0.4,
                # Ruang keluaran cukup agar JSON tidak terpotong.
                max_completion_tokens=4000,
                **settings.opsi_model(self.model),
            )
            catat("rekomendasi_judul", chat_completion.model or self.model,
                  chat_completion.usage.prompt_tokens if chat_completion.usage else 0,
                  chat_completion.usage.completion_tokens if chat_completion.usage else 0,
                  int((time.monotonic() - mulai) * 1000), True)
            return chat_completion.choices[0].message.content

        except Exception as e:
            catat("rekomendasi_judul", self.model, durasi_ms=int((time.monotonic() - mulai) * 1000), berhasil=False)
            print(f"Error calling OpenAI API : {e}")
            raise

    def _validate_response(self, response: Dict[str, Any]) -> None:
        if "rekomendasi" not in response:
            raise ValueError("Response tidak mengandung key 'rekomendasi'.")

        if not isinstance(response["rekomendasi"], list):
            raise ValueError(" 'Rekomendasi' harus berupa list")

        if len(response["rekomendasi"]) == 0:
            raise ValueError("List Rekomendasi Kosong")

        # Validasi setiap rekomendasi memiliki kata kunci
        for i, rec in enumerate(response["rekomendasi"]):
            if "keywords" not in rec:
                print(
                    f"Warning: Rekomendasi #{i+1} tidak memiliki 'keywords', akan gunakan fallback.")

    def _rapikan(self, response: Dict[str, Any], daftar_tema: list) -> None:
        """Samakan bentuk keluaran AI: tema harus dari daftar, metodologi berupa teks."""
        baku = {str(t).strip().casefold(): t for t in daftar_tema}
        for rec in response["rekomendasi"]:
            rec["tema"] = baku.get(str(rec.get("tema", "")).strip().casefold(), "Lainnya")
            if isinstance(rec.get("metodologi"), list):
                rec["metodologi"] = "\n".join(str(x) for x in rec["metodologi"])
            rec["judul"] = str(rec.get("judul", "")).strip()[:300]

    def _add_real_references(
        self,
        recommendations: Dict[str, Any]
    ) -> Dict[str, Any]:
        for i, rec in enumerate(recommendations['rekomendasi']):
            print(f" Mengambil referensi untuk rekomendasi #{i+1}...")

            # Get keywords dari AI response
            keywords = rec.get('keywords', [])

            # Fallback jika keywords tidak ada
            if not keywords:
                keywords = self._extract_keywords_from_title(
                    rec.get('judul', ''))

            print(f"  Keywords: {keywords}")

            # Search paper dari Semantic Scholar
            try:
                papers = reference_service.search_papers(
                    keywords=keywords,
                    limit=3,
                    min_citations=5
                )

                print(f"  Ditemukan {len(papers)} paper relevan.")

                # Add papers sebagai referensi
                rec["referensi"] = papers
            except Exception as e:
                print(f"  Gagal mengambil referensi: {e}")
                # Fallback untuk mencari referensi manual
                rec["referensi"] = reference_service._get_fallback_references(
                    keywords)

        return recommendations

    def _extract_keywords_from_title(self, title: str) -> list[str]:
        # Stopwords yang tidak penting
        stopwords = {
            'sistem', 'aplikasi', 'menggunakan', 'dengan', 'untuk',
            'berbasis', 'pada', 'di', 'dan', 'atau', 'yang'
        }

        # Split title dan filter stopwords
        words = title.lower().split()
        keywords = [
            word for word in words
            if word not in stopwords and len(word) > 3
        ]

        return keywords[:3]


ai_service = AIService()
