import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env si existe
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Configuración del servidor
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Configuración de Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Configuración del Scraper
DEFAULT_MAX_VIDEOS = int(os.getenv("DEFAULT_MAX_VIDEOS", "10"))
PAGE_TIMEOUT_MS = int(os.getenv("PAGE_TIMEOUT_MS", "45000"))
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "false").lower() == "true"

def get_gemini_api_key(override_key: str | None = None) -> str | None:
    """
    Retorna la API Key de Gemini:
    1. Si se pasa override_key (ej. desde el frontend), tiene prioridad.
    2. Si no, busca la variable de entorno GEMINI_API_KEY.
    """
    if override_key and override_key.strip():
        return override_key.strip()
    return GEMINI_API_KEY if GEMINI_API_KEY else None
