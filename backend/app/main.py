from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.diagnostic import router as diagnostic_router
from app.api.learning import router as learning_router
from app.api.mypage import router as mypage_router
from app.api.vocabulary import router as vocabulary_router
from app.core.config import ALLOWED_ORIGINS
from app.db.supabase import supabase

app = FastAPI(
    title="TOEIC AI API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(diagnostic_router)
app.include_router(learning_router)
app.include_router(auth_router)
app.include_router(mypage_router)
app.include_router(vocabulary_router)
app.include_router(ai_router)


@app.get("/health")
def health():
    return {
        "ok": True,
        "message": "TOEIC AI backend is running",
    }


@app.get("/health/db")
def health_db():
    response = supabase.table("test_connection").select("*").limit(1).execute()

    return {
        "ok": True,
        "data": response.data,
    }
