import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from models.schemas import ChatInput, UserInput
from services.ai_service import ai_service
from services.obrolan_service import obrolan_service

# Inisialisasi FastAPI app

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DECRIPTION,
    version=settings.API_VERSION,
)

# Middleware CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints


@app.get("/")
async def root():
    return {
        "status": "Online",
        "message": "Chatbot API is running",
        "version": settings.API_VERSION
    }

# For Railway deployment
port = int(os.environ.get("PORT", 8000))


@app.post("/get-recommendations")
async def get_recommendations(user_input: UserInput):
    try:
        recommendations = ai_service.get_recommendations(
            user_input.interests, user_input.prodi, user_input.mata_kuliah, user_input.tema, user_input.diskusi)
        return recommendations
    except ValueError as e:
        # Error validasi input
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Error lainnya
        # Rincian galat hanya di log; jangan diteruskan ke pemanggil.
        print(f"Terjadi error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Rekomendasi belum dapat disusun. Coba lagi beberapa saat lagi."
        )


# Endpoint sinkron (def) agar panggilan AI yang lama tidak menahan permintaan lain.
@app.post("/chat")
def chat(masukan: ChatInput):
    try:
        return obrolan_service.balas(
            [p.model_dump() for p in masukan.pesan], masukan.prodi, masukan.mata_kuliah, masukan.tema,
            masukan.kandidat)
    except Exception as e:
        print(f"Terjadi error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Balasan belum dapat disusun. Coba lagi beberapa saat lagi.")
