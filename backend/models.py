"""
==============================================================================
MÓDULO: backend/models.py
PROPÓSITO:
    Define las estructuras de datos (esquemas) fuertemente tipadas mediante
    Pydantic para todo el ciclo de vida de la aplicación.

CÓMO INTERACTÚA CON EL RESTO DEL SISTEMA:
    1. 'scraper.py' construye instancias de 'VideoData' y 'ProfileData' conforme
       intercepta paquetes JSON y parsea el DOM de TikTok.
    2. 'analyzer.py' toma un 'ProfileData' y produce un 'BigFiveAnalysis'
       con sus respectivos 'BigFiveTrait' y 'SentimentAnalysis'.
    3. 'video_analyzer.py' recibe 'VideoAnalysisRequest' y devuelve 'VideoAnalysisResponse'.
    4. 'app.py' usa estos modelos en 'response_model' para que FastAPI valide
       las respuestas JSON que viajan al Frontend y genere la documentación OpenAPI.
==============================================================================
"""

# ==============================================================================
# 1. IMPORTACIÓN DE LIBRERÍAS Y EL PORQUÉ DE CADA UNA
# ==============================================================================

# 'typing' proporciona anotaciones de tipos estándar de Python:
# - 'List': listas homogéneas (ej. lista de comentarios de texto).
# - 'Dict': diccionarios clave-valor para mapeos flexibles.
# - 'Optional': campos que pueden contener un valor o ser 'None' (opcionales).
# - 'Any': comodín para estructuras heterogéneas.
from typing import List, Dict, Optional, Any

# 'BaseModel' y 'Field' de 'pydantic':
# - 'BaseModel': clase base que convierte clases ordinarias en esquemas validados
#   con serialización automática bidireccional (Python <-> JSON).
# - 'Field': añade metadatos de validación (rangos numéricos 'ge', 'le', descripciones).
from pydantic import BaseModel, Field


# ==============================================================================
# 2. MODELOS DE DATOS PARA SCRAPING DE TIKTOK
# ==============================================================================

class VideoData(BaseModel):
    """
    Representa la información individual de un video extraído de TikTok.
    
    ¿POR QUÉ EXISTE?:
        Almacena de forma ordenada las métricas de interacción, URL directa,
        miniatura y los comentarios más recientes para alimentar tanto las
        tarjetas del frontend como el motor de análisis multimodal.
    """
    video_id: str                      # Identificador numérico único de la publicación en TikTok
    url: str                           # Enlace web directo al video (https://www.tiktok.com/@.../video/...)
    description: str = ""              # Pie de publicación (caption) escrito por el creador
    likes: int = 0                     # Total de 'Me gusta' ('diggCount')
    comments_count: int = 0            # Total de comentarios registrados en el video ('commentCount')
    saves: int = 0                     # Total de guardados en favoritos ('collectCount')
    shares: int = 0                    # Total de veces compartido ('shareCount')
    comments_list: List[str] = Field(
        default_factory=list,
        description="Lista de comentarios textuales capturados en el formato '@usuario: texto'"
    )
    cover_url: Optional[str] = None    # URL de la imagen de portada/miniatura del video
    duration: Optional[int] = 0        # Duración del video en segundos
    create_time: Optional[int] = None  # Timestamp UNIX de la fecha de publicación


# ==============================================================================
# 3. MODELOS PARA EL ANÁLISIS PSICOLÓGICO BIG FIVE (OCEAN)
# ==============================================================================

class BigFiveTrait(BaseModel):
    """
    Representa uno de los cinco rasgos psicométricos del modelo OCEAN:
    (Apertura, Responsabilidad, Extraversión, Amabilidad o Neuroticismo).

    ¿POR QUÉ EXISTE?:
        Permite que cada rasgo tenga una puntuación normalizada de 0 a 100,
        un nivel cualitativo entendible por humanos y los argumentos observados.
    """
    score: int = Field(..., ge=0, le=100, description="Puntuación psicométrica normalizada de 0 a 100")
    level: str = Field(..., description="Nivel categórico: 'Alto', 'Medio' o 'Bajo'")
    summary: str = Field(..., description="Resumen descriptivo del rasgo en el creador analizado")
    characteristics: List[str] = Field(
        default_factory=list,
        description="Indicadores o evidencias empíricas observadas en los datos del perfil"
    )


class SentimentBreakdown(BaseModel):
    """
    Desglose porcentual de la polaridad emocional del contenido y la comunidad.
    
    ¿POR QUÉ EXISTE?:
        Alimenta directamente el gráfico de rosquilla (Doughnut Chart) en el frontend.
    """
    positive: int = 0  # Porcentaje de comentarios y contenido positivo (0-100%)
    neutral: int = 0   # Porcentaje de comentarios y contenido neutral (0-100%)
    negative: int = 0  # Porcentaje de comentarios y contenido crítico/negativo (0-100%)


class SentimentAnalysis(BaseModel):
    """
    Evaluación integral de la sensibilidad y clima emocional de la cuenta.

    ¿POR QUÉ EXISTE?:
        Diagnostica la relación afectiva entre el creador y su comunidad.
    """
    overall: str = "Neutro"            # Clasificación general (ej. 'Positivo', 'Inspirador', 'Crítico')
    score: float = 0.0                 # Polaridad matemática continua en escala de -1.0 a +1.0
    breakdown: SentimentBreakdown = Field(default_factory=SentimentBreakdown)
    dominant_emotions: List[str] = Field(
        default_factory=list,
        description="Etiquetas de emociones detectadas (ej. 'Entusiasmo', 'Curiosidad', 'Humor')"
    )
    community_tone: str = ""           # Descripción cualitativa del comportamiento del público en comentarios


class BigFiveAnalysis(BaseModel):
    """
    Informe completo del perfil de personalidad según el modelo de los Cinco Grandes (OCEAN).

    ¿POR QUÉ EXISTE?:
        Es el objeto principal devuelto por 'analyzer.py' que agrupa las 5 dimensiones
        psicológicas, la síntesis narrativa, las fortalezas y el modelo de IA utilizado.
    """
    openness: BigFiveTrait             # O: Apertura a la experiencia (creatividad, novedad)
    conscientiousness: BigFiveTrait    # C: Responsabilidad (disciplina, estructura)
    extraversion: BigFiveTrait         # E: Extraversión (energía social, asertividad)
    agreeableness: BigFiveTrait        # A: Amabilidad (empatía, cooperación)
    neuroticism: BigFiveTrait          # N: Estabilidad emocional / Neuroticismo
    general_summary: str               # Párrafo de síntesis sobre el perfil global del creador
    communication_style: str           # Diagnóstico del estilo comunicativo hacia sus seguidores
    key_strengths: List[str] = Field(
        default_factory=list,
        description="Puntos fuertes destacados del creador en redes sociales"
    )
    sentiment: SentimentAnalysis       # Diagnóstico de sentimiento y comunidad asociado
    model_used: str = "Gemini AI"      # Identificador del modelo ejecutor (Gemini o Heurístico)


# ==============================================================================
# 4. MODELO COMPLETO DEL PERFIL DE USUARIO
# ==============================================================================

class ProfileData(BaseModel):
    """
    Objeto raíz que encapsula toda la información extraída de una cuenta de TikTok.

    ¿POR QUÉ EXISTE?:
        Es el contenedor final que viaja del Backend al Frontend en la ruta '/api/scrape/{username}'.
        Incluye tanto los datos crudos extraídos de la red como el análisis psicológico computado.
    """
    username: str                                  # @nombre_de_usuario de la cuenta
    name: str = ""                                 # Nombre público visible del perfil
    followers: int = 0                             # Total de seguidores
    following: int = 0                             # Total de cuentas seguidas
    bio: Optional[str] = ""                        # Biografía o firma del usuario
    avatar_url: Optional[str] = None               # Enlace a la imagen de foto de perfil
    videos: List[VideoData] = Field(default_factory=list) # Lista con los videos analizados (típicamente 10)
    analysis: Optional[BigFiveAnalysis] = None     # Informe de personalidad (si ya fue procesado)


# ==============================================================================
# 5. MODELOS PARA EL ANÁLISIS MULTIMODAL DE VIDEOS INDIVIDUALES
# ==============================================================================

class VideoAnalysisRequest(BaseModel):
    """
    Petición enviada desde el Frontend para analizar a fondo un video en particular.

    ¿POR QUÉ EXISTE?:
        Permite enviar la información necesaria (id, portada, descripción, comentarios)
        al endpoint '/api/analyze-video' cuando el usuario presiona '✨ Analizar Video con IA'.
    """
    video_id: str
    url: str
    description: str = ""
    comments: List[str] = Field(default_factory=list)
    cover_url: Optional[str] = None
    api_key: Optional[str] = None                  # Permite pasar una clave personalizada para esta consulta


class VideoAnalysisResponse(BaseModel):
    """
    Resultado del análisis multimodal de un video individual.

    ¿POR QUÉ EXISTE?:
        Estructura la respuesta de la IA (estilo visual, tono, indicios de personalidad)
        para mostrarla de forma atractiva en el modal emergente de video del frontend.
    """
    video_id: str
    topic_category: str                            # Categoría tematica (Educación, Lifestyle, Comedia, etc.)
    visual_and_production_style: str               # Evaluación de encuadre, dinamismo y formato visual
    emotional_tone: str                            # Tono emocional observado
    audience_reaction: str                         # Conclusión sobre cómo reaccionó la audiencia
    personality_cues: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapeo de rasgos observados específicamente en este video (ej. Extraversión: alta)"
    )
    key_takeaways: List[str] = Field(
        default_factory=list,
        description="Lecciones o conclusiones principales del contenido"
    )
    model_used: str = "Gemini AI"                  # Motor que resolvió el análisis
