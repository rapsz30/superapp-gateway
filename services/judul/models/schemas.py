
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class UserInput(BaseModel):
    interests: str = Field(
        ...,
        max_length=300,
        description="Minat atau topik yang diminati untuk tugas akhir",
        example="Machine Learning dan Cyber Security"
    )
    # Konteks dari layanan identity; kosong bila dipanggil langsung.
    prodi: str = Field("", max_length=200)
    mata_kuliah: List[str] = Field(default_factory=list, max_length=20)
    tema: List[str] = Field(default_factory=list, max_length=30)
    # Cuplikan diskusi brainstorm, agar judul mengikuti arah yang sudah dibicarakan.
    diskusi: str = Field("", max_length=3000)


class Pesan(BaseModel):
    peran: Literal["mahasiswa", "asisten"]
    isi: str = Field(..., min_length=1, max_length=2000)


class ChatInput(BaseModel):
    pesan: List[Pesan] = Field(..., min_length=1, max_length=20)
    prodi: str = Field("", max_length=200)
    mata_kuliah: List[str] = Field(default_factory=list, max_length=20)
    tema: List[str] = Field(default_factory=list, max_length=30)
    # Diisi bila yang dibahas satu kandidat judul.
    kandidat: Optional[dict] = None


class Reference(BaseModel):
    sitasi: str
    link: str


class Recommendation(BaseModel):
    judul: str
    tema: str = "Lainnya"
    deskripsi: str
    metodologi: str
    keywords: List[str] = []
    referensi: List[Reference] = []


class RecommendationResponse(BaseModel):
    rekomendasi: List[Recommendation]
