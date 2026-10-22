import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import HOST, PORT, GEMINI_API_KEY, DEFAULT_MAX_VIDEOS
from backend.models import (
    ProfileData,
    BigFiveAnalysis,
    VideoAnalysisRequest,
    VideoAnalysisResponse,
)
from backend.scraper import run_scraper_in_proactor
from backend.analyzer import perform_bigfive_analysis
from backend.video_analyzer import analyze_single_video

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

app = FastAPI(
    title="Scrappy TikTok - Analytics & Big Five Personality Engine",
    description="Extractor de métricas de TikTok con análisis de rasgos de personalidad Big Five (OCEAN) y análisis multimodal de video.",
    version="2.0.0"
)

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos si la carpeta existe
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Sirve la interfaz gráfica moderna del Frontend."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Frontend no encontrado en frontend/index.html</h1>", status_code=404)
    return FileResponse(str(index_path))


@app.get("/api/health")
async def health_check():
    """Verifica el estado del servicio y la disponibilidad de Gemini AI."""
    return {
        "status": "online",
        "platform": sys.platform,
        "gemini_configured": bool(GEMINI_API_KEY),
        "default_max_videos": DEFAULT_MAX_VIDEOS
    }


@app.post("/api/test-key")
async def test_gemini_key(payload: dict):
    """
    Verifica si una clave API de Gemini proporcionada por el usuario es válida.
    """
    key = payload.get("api_key", "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Debe ingresar una API Key para validar.")

    try:
        from google import genai
        client = genai.Client(api_key=key)
        # Prueba de generación ligera
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Responde solo 'OK' para verificar la conexión.",
        )
        return {
            "valid": True,
            "message": "¡API Key de Gemini verificada y operativa!",
            "model": "gemini-2.5-flash"
        }
    except Exception as e:
        return {
            "valid": False,
            "message": f"Error al validar la clave: {str(e)}"
        }


@app.get("/api/scrape/{username}", response_model=ProfileData)
async def api_scrape_and_analyze(
    username: str,
    max_videos: int = Query(default=10, ge=1, le=30),
    api_key: Optional[str] = Query(default=None)
):
    """
    Endpoint principal:
    1. Extrae el perfil y los videos del usuario con Playwright en Windows.
    2. Ejecuta automáticamente el análisis Big Five (OCEAN) y análisis de sentimiento.
    """
    clean_username = username.strip().lstrip("@")
    if not clean_username:
        raise HTTPException(status_code=400, detail="El nombre de usuario no puede estar vacío.")

    # 1. Scraping ejecutado en hilo con Proactor loop
    profile: ProfileData = await asyncio.to_thread(
        run_scraper_in_proactor, clean_username, max_videos
    )

    # 2. Análisis psicológico Big Five y Sentimiento
    analysis: BigFiveAnalysis = perform_bigfive_analysis(profile, override_api_key=api_key)
    profile.analysis = analysis

    return profile


@app.post("/api/analyze-bigfive", response_model=BigFiveAnalysis)
async def api_reanalyze_bigfive(payload: dict):
    """
    Reanaliza un perfil ya extraído utilizando una nueva API Key de Gemini o parámetros ajustados.
    """
    profile_data = payload.get("profile")
    api_key = payload.get("api_key")

    if not profile_data:
        raise HTTPException(status_code=400, detail="Faltan los datos del perfil ('profile').")

    profile = ProfileData(**profile_data)
    analysis = perform_bigfive_analysis(profile, override_api_key=api_key)
    return analysis


@app.post("/api/analyze-video", response_model=VideoAnalysisResponse)
async def api_analyze_video(request: VideoAnalysisRequest):
    """
    Analiza a fondo un video individual de TikTok mediante IA multimodal (portada + texto + comentarios).
    """
    return await analyze_single_video(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=True)
