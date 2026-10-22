"""
==============================================================================
MÓDULO: backend/config.py
PROPÓSITO:
    Centraliza y gestiona todas las variables de entorno, constantes globales y
    parámetros de configuración del sistema (FastAPI, Gemini AI y Playwright).

CÓMO INTERACTÚA CON EL RESTO DEL SISTEMA:
    1. 'app.py' lo importa para obtener la dirección IP y puerto del servidor.
    2. 'scraper.py' lo usa para saber si debe abrir el navegador en modo visible
       o headless, y el tiempo máximo de espera (timeout) al cargar perfiles.
    3. 'analyzer.py' y 'video_analyzer.py' utilizan 'get_gemini_api_key()' y
       'DEFAULT_GEMINI_MODEL' para saber con qué credenciales y modelo conectar
       a la API de Google Gemini.
==============================================================================
"""

# ==============================================================================
# 1. IMPORTACIÓN DE LIBRERÍAS Y EL PORQUÉ DE CADA UNA
# ==============================================================================

# 'os' proporciona funciones del sistema operativo para leer variables de entorno
# como GEMINI_API_KEY, HOST y PORT de forma segura sin exponer credenciales en el código.
import os

# 'Path' de 'pathlib' permite manipular rutas de archivos y directorios de forma
# agnóstica al sistema operativo (Windows, macOS o Linux) evitando errores de barras '/' vs '\'.
from pathlib import Path

# 'load_dotenv' lee archivos de texto con formato .env e inyecta sus variables
# en 'os.environ' para que puedan ser leídas por la aplicación.
from dotenv import load_dotenv


# ==============================================================================
# 2. LOCALIZACIÓN Y CARGA DE VARIABLES DE ENTORNO
# ==============================================================================

# Calculamos la ruta absoluta del directorio raíz del proyecto (dos niveles arriba de este archivo).
# ¿POR QUÉ?: Para asegurar que no importe desde qué carpeta se ejecute 'python run.py',
# el sistema siempre encuentre el archivo '.env' correcto.
BASE_DIR = Path(__file__).resolve().parent.parent

# Intentamos cargar el archivo '.env' principal.
# Si el usuario aún no ha creado '.env' pero configuró '.env.example', lo usamos como respaldo.
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    example_path = BASE_DIR / ".env.example"
    if example_path.exists():
        load_dotenv(example_path)


# ==============================================================================
# 3. CONSTANTES GLOBALES DE CONFIGURACIÓN
# ==============================================================================

# Dirección IP donde escuchará el servidor FastAPI (127.0.0.1 = localhost).
HOST: str = os.getenv("HOST", "127.0.0.1")

# Puerto de red donde responderá la API web y el frontend.
PORT: int = int(os.getenv("PORT", "8000"))

# Clave de autenticación para los servicios de Google Gemini AI.
# Si está vacía, el sistema alternará automáticamente al motor heurístico local.
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()

# Modelo de IA seleccionado por defecto. Usamos 'gemini-3.5-flash-lite'
# por ser la versión más rápida, estable y de menor latencia activa en la API.
DEFAULT_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Cantidad máxima de videos a extraer y analizar por cada perfil de TikTok.
DEFAULT_MAX_VIDEOS: int = int(os.getenv("DEFAULT_MAX_VIDEOS", "10"))

# Tiempo límite en milisegundos (45 segundos) para que Playwright cargue una página de TikTok
# antes de lanzar una excepción por lentitud o bloqueo de red.
PAGE_TIMEOUT_MS: int = int(os.getenv("PAGE_TIMEOUT_MS", "45000"))

# Define si Chromium se ejecuta en segundo plano sin ventana gráfica ('true')
# o visible ('false'). Por defecto es 'false' para esquivar mejor las detecciones de bots.
HEADLESS_MODE: bool = os.getenv("HEADLESS_MODE", "false").lower() == "true"


# ==============================================================================
# 4. FUNCIONES HELPER / DE UTILIDAD
# ==============================================================================

def get_gemini_api_key(override_key: str | None = None) -> str | None:
    """
    Determina la clave de API de Gemini a utilizar respetando la jerarquía de prioridad:
    
    PARÁMETROS:
        override_key (str | None): Clave enviada directamente desde la interfaz web
                                   o en los parámetros de la solicitud HTTP.

    RETORNO:
        str | None: La clave prioritaria, o None si no hay ninguna configurada.

    JERARQUÍA DE DECISIÓN:
        1. Si el usuario ingresó una clave en la interfaz web (override_key), se usa esa.
        2. Si no, se recurre a la variable 'GEMINI_API_KEY' del archivo .env.
        3. Si ninguna existe, retorna None (lo que activará el modo heurístico sin fallar).
    """
    if override_key and override_key.strip():
        return override_key.strip()
    return GEMINI_API_KEY if GEMINI_API_KEY else None
