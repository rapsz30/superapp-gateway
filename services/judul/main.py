import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send
from ai_usage import akun_id

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


class UserContextMiddleware:
    def __init__(self, app: ASGIApp): self.app = app
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        value = headers.get(b"x-user-id", b"").decode("utf-8", "ignore") or None
        token = akun_id.set(value)
        try:
            await self.app(scope, receive, send)
        finally:
            akun_id.reset(token)


app.add_middleware(UserContextMiddleware)

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
