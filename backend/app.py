"""
==============================================================================
MÓDULO: backend/app.py
PROPÓSITO:
    Servidor web principal desarrollado con FastAPI.
    Expone la API REST para el cliente frontend, gestiona el ciclo de vida
    de las peticiones, monta los archivos estáticos y orquesta el scraping
    y los análisis de inteligencia artificial.

CÓMO INTERACTÚA CON EL RESTO DEL SISTEMA:
    1. 'run.py' ejecuta este archivo indicando 'backend.app:app' a Uvicorn.
    2. Sirve 'frontend/index.html' en la ruta raíz ('/').
    3. Monta la carpeta 'frontend/static' en '/static' para entregar estilos CSS y JS.
    4. En '/api/scrape/{username}': coordina a 'scraper.py' (para obtener los datos)
       y a 'analyzer.py' (para computar el Big Five y sentimiento).
    5. En '/api/analyze-video': delega la inferencia multimodal a 'video_analyzer.py'.
    6. En '/api/test-key': permite al usuario validar su Gemini API Key desde la UI.
==============================================================================
"""

# ==============================================================================
# 1. IMPORTACIÓN DE LIBRERÍAS Y EL PORQUÉ DE CADA UNA
# ==============================================================================

# 'asyncio' permite ejecutar tareas bloqueantes en hilos separados con 'asyncio.to_thread'
# para que el servidor web no se congele durante el scraping con Playwright.
import asyncio

# 'os' interactúa con rutas del sistema y variables de entorno del servidor.
import os

# 'sys' reporta la plataforma operativa en el endpoint de diagnóstico de salud ('/api/health').
import sys

# 'Path' de 'pathlib' resuelve las rutas relativas hacia la carpeta frontend/ y estáticos.
from pathlib import Path

# 'Optional' permite declarar parámetros de consulta (query params) opcionales en FastAPI.
from typing import Optional

# Componentes fundamentales de FastAPI:
# - 'FastAPI': instancia principal de la aplicación web y router de endpoints.
# - 'HTTPException': lanza respuestas HTTP de error con código y mensaje descriptivo.
# - 'Query': valida y restringe los parámetros que vienen en la URL (ej. límites numéricos).
from fastapi import FastAPI, HTTPException, Query

# 'CORSMiddleware' habilita Cross-Origin Resource Sharing para permitir que
# clientes frontend en diferentes dominios o puertos se comuniquen con la API sin bloqueos del navegador.
from fastapi.middleware.cors import CORSMiddleware

# 'HTMLResponse' y 'FileResponse' entregan contenido web y archivos directamente al navegador.
from fastapi.responses import HTMLResponse, FileResponse

# 'StaticFiles' mapea un directorio local del disco como un servidor de archivos estáticos (CSS, JS, iconos).
from fastapi.staticfiles import StaticFiles

# Constantes y configuraciones globales del servidor.
from backend.config import HOST, PORT, GEMINI_API_KEY, DEFAULT_MAX_VIDEOS

# Modelos Pydantic para validación y serialización de peticiones y respuestas.
from backend.models import (
    ProfileData,
    BigFiveAnalysis,
    VideoAnalysisRequest,
    VideoAnalysisResponse,
)

# Motor de scraping aislado para Windows.
from backend.scraper import run_scraper_in_proactor

# Motores de análisis psicológico y multimodal.
from backend.analyzer import perform_bigfive_analysis, generate_content_with_fallback
from backend.video_analyzer import analyze_single_video


# ==============================================================================
# 2. DEFINICIÓN DE RUTAS Y CONFIGURACIÓN DE LA APLICACIÓN
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

# Instancia central de FastAPI con metadatos de documentación OpenAPI
app = FastAPI(
    title="Scrappy TikTok - Analytics & Big Five Personality Engine",
    description="Extractor de métricas de TikTok con análisis de rasgos de personalidad Big Five (OCEAN) y análisis multimodal de video.",
    version="2.0.0"
)

# Configuramos CORS para admitir peticiones desde cualquier origen (útil en desarrollo local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montamos la carpeta de archivos estáticos (/static/css, /static/js) si existe
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ==============================================================================
# 3. ENDPOINTS DEL SERVIDOR
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """
    Entrega el archivo 'frontend/index.html' cuando el usuario entra a http://127.0.0.1:8000.
    
    RETORNO:
        FileResponse con el contenido HTML moderno del Dashboard.
    """
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Frontend no encontrado en frontend/index.html</h1>", status_code=404)
    return FileResponse(str(index_path))


@app.get("/api/health")
async def health_check():
    """
    Comprueba el estado del backend y la disponibilidad de Gemini AI.
    
    ¿POR QUÉ EXISTE?:
        El frontend consulta este endpoint al iniciar para pintar la insignia
        de estado ('🟢 Gemini AI Activo' o '🟡 Modo Heurístico Local').
    """
    return {
        "status": "online",
        "platform": sys.platform,
        "gemini_configured": bool(GEMINI_API_KEY),
        "default_max_videos": DEFAULT_MAX_VIDEOS
    }


@app.post("/api/test-key")
async def test_gemini_key(payload: dict):
    """
    Valida en tiempo real una clave de Gemini proporcionada por el usuario en la interfaz.

    PARÁMETROS:
        payload (dict): Diccionario que contiene la clave {'api_key': '...'} a probar.

    RETORNO:
        dict: {'valid': True/False, 'message': '...', 'model': '...'}
    """
    key = payload.get("api_key", "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Debe ingresar una API Key para validar.")

    try:
        from google import genai
        client = genai.Client(api_key=key)
        
        # Realizamos una prueba ligera de generación con el sistema de fallback tolerante a fallos
        res, used_model = generate_content_with_fallback(
            client=client,
            contents="Responde solo 'OK' para verificar la conexión.",
        )
        return {
            "valid": True,
            "message": f"¡API Key de Gemini verificada y operativa con modelo '{used_model}'!",
            "model": used_model
        }
    except Exception as e:
        return {
            "valid": False,
            "message": f"Error al validar la clave: {str(e)}"
        }


@app.get("/api/scrape/{username}", response_model=ProfileData)
async def api_scrape_and_analyze(
    username: str,
    max_videos: int = Query(default=10, ge=1, le=30, description="Cantidad de videos a inspeccionar (entre 1 y 30)"),
    api_key: Optional[str] = Query(default=None, description="API Key opcional enviada desde el cliente")
):
    """
    Ruta principal del sistema:
    
    FLUJO DE INTERACCIÓN:
        1. Recibe el nombre de usuario de TikTok a través de la URL.
        2. Ejecuta 'run_scraper_in_proactor' en un hilo separado ('asyncio.to_thread')
           para que Playwright extraiga el perfil sin bloquear el servidor web.
        3. Pasa el 'ProfileData' obtenido a 'perform_bigfive_analysis' de 'analyzer.py'.
        4. Inyecta el resultado del análisis en 'profile.analysis'.
        5. Retorna el objeto unificado 'ProfileData' validado con Pydantic.
    """
    clean_username = username.strip().lstrip("@")
    if not clean_username:
        raise HTTPException(status_code=400, detail="El nombre de usuario no puede estar vacío.")

    # 1. Extracción con Playwright en Windows Proactor loop aislado
    profile: ProfileData = await asyncio.to_thread(
        run_scraper_in_proactor, clean_username, max_videos
    )

    # 2. Análisis psicométrico Big Five y Sentimiento (Gemini o Heurístico de respaldo)
    analysis: BigFiveAnalysis = perform_bigfive_analysis(profile, override_api_key=api_key)
    profile.analysis = analysis

    return profile


@app.post("/api/analyze-bigfive", response_model=BigFiveAnalysis)
async def api_reanalyze_bigfive(payload: dict):
    """
    Reanaliza un perfil ya extraído previamente sin necesidad de volver a scrapear TikTok.
    
    ¿POR QUÉ EXISTE?:
        Si el usuario realizó el scraping inicial sin clave de Gemini y luego decide
        ingresarla en los ajustes, puede pulsar '✨ Reanalizar' para enriquecer los datos
        de inmediato en segundos.
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
    Ejecuta el análisis multimodal de un video individual seleccionado.

    ¿POR QUÉ EXISTE?:
        Responde a la acción '✨ Analizar Video con IA' de las tarjetas de video del frontend,
        examinando la imagen de miniatura, caption y comentarios con Gemini Multimodal.
    """
    return await analyze_single_video(request)


# ==============================================================================
# 4. PUNTO DE ENTRADA DIRECTO
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    # Permite iniciar el servidor con recarga en caliente automática si se modifica código
    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=True)
