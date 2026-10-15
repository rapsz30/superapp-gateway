
from pydantic import BaseModel, Field
from typing import List, Optional


class UserInput(BaseModel):
    interests: str = Field(
        ...,
        description="Minat atau topik yang diminati untuk tugas akhir",
        example="Machine Learning dan Cyber Security"
    )


class Reference(BaseModel):
    sitasi: str
    link: str


class Recommendation(BaseModel):
    judul: str
    deskripsi: str
    metodologi: str
    keywords: List[str] = []
    referensi: List[Reference] = []


class RecommendationResponse(BaseModel):
    rekomendasi: List[Recommendation]
