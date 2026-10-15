import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from models.schemas import UserInput
from services.ai_service import ai_service

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
            user_input.interests)
        return recommendations
    except ValueError as e:
        # Error validasi input
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Error lainnya
        print(f"Terjadi error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan internal : {e}"
        )
