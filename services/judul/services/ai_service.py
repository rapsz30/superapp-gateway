# INTERAKSI DENGAN LAYANAN AI

import json
from typing import Dict, Any
import time

from config.settings import settings
from services.prompt_service import prompt_service
from services.reference_service import reference_service


class AIService:
    """ Handle interaksi dengan AI """

    def __init__(self):
        # Inisialisasi AI service dengan Groq client
        self.client = settings.get_groq_client()
        self.model = settings.GROQ_MODEL

    def get_recommendations(self, interests: str) -> Dict[str, Any]:
        # Validasi input
        if not interests or not interests.strip():
            raise ValueError("Interests tidak boleh kosong.")

        print("="*50)
        print("STEP 1: Generate Recommendation with AI... ")

        # Generate prompt
        prompt = prompt_service.create_recommendation_prompt(interests)

        # Call AI
        response_content = self._call_groq_api(prompt)

        # Parse JSON response
        recommendations = json.loads(response_content)

        # Validate structure
        self._validate_response(recommendations)

        print("STEP 2: AI generated recommendations successfully.")
        print(
            f"Total Recommendations: {len(recommendations.get('rekomendasi', []))}")

        # Fetch real references
        print("STEP 3: Fetching real references from Semantic Scholar... ")
        recommendations_with_refs = self._add_real_references(recommendations)

        print("STEP 4: Process completed!")
        print("="*50)

        return recommendations_with_refs

    def _call_groq_api(self, prompt: str) -> str:
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
            )
            return chat_completion.choices[0].message.content

        except Exception as e:
            print(f"Error calling Groq API : {e}")
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
