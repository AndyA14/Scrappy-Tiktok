"""
==============================================================================
MÓDULO: backend/video_analyzer.py
PROPÓSITO:
    Motor de análisis multimodal especializado en publicaciones individuales de TikTok.
    Evalúa la miniatura visual, la narrativa, el estilo de producción y la recepción
    de la audiencia para un video en particular.

CÓMO INTERACTÚA CON EL RESTO DEL SISTEMA:
    1. 'app.py' lo invoca en la ruta POST '/api/analyze-video' cuando el usuario
       hace clic en el botón '✨ Analizar Video con IA' dentro de una tarjeta de video.
    2. Utiliza 'httpx' para descargar de forma asíncrona los bytes de la portada/miniatura ('cover_url').
    3. Si hay API Key de Gemini: convierte la imagen en un 'types.Part.from_bytes'
       y la envía junto con el prompt a 'generate_content_with_fallback()' de 'analyzer.py'.
    4. Si NO hay API Key: activa '_analyze_video_heuristic()' clasificando por patrones
       semánticos y ratios de interacción.
    5. Retorna 'VideoAnalysisResponse' estructurado para alimentar el modal interactivo de la UI.
==============================================================================
"""

# ==============================================================================
# 1. IMPORTACIÓN DE LIBRERÍAS Y EL PORQUÉ DE CADA UNA
# ==============================================================================

# 'json' procesa los datos estructurados en formato JSON entre el LLM y la aplicación.
import json

# 'logging' emite mensajes de advertencia o diagnóstico si falla la descarga de una miniatura.
import logging

# 're' se encarga de sanear la respuesta textual eliminando posibles bloques markdown.
import re

# 'typing' proporciona anotaciones estáticas para mayor robustez en los parámetros.
from typing import Optional, List

# 'httpx' es un cliente HTTP asíncrono de alto rendimiento.
# ¿POR QUÉ?: Permite descargar las imágenes de portada (miniaturas) de TikTok
# de forma no bloqueante sin detener el hilo principal de FastAPI.
import httpx

# Modelos Pydantic para validar la petición y estructurar la respuesta.
from backend.models import VideoAnalysisRequest, VideoAnalysisResponse

# Configuración de credenciales y modelo predeterminado de Gemini.
from backend.config import get_gemini_api_key, DEFAULT_GEMINI_MODEL

# Función de fallback automático compartida con 'analyzer.py' para tolerar modelos retirados.
from backend.analyzer import generate_content_with_fallback

# Logger especializado para este módulo.
logger = logging.getLogger("scrappy.video_analyzer")


# ==============================================================================
# 2. FUNCIÓN PRINCIPAL DE ANÁLISIS DE VIDEO
# ==============================================================================

async def analyze_single_video(req: VideoAnalysisRequest) -> VideoAnalysisResponse:
    """
    Coordina la evaluación de un video individual combinando visión artificial y PLN.

    PARÁMETROS:
        req (VideoAnalysisRequest): Datos del video (id, url, caption, comentarios, portada).

    RETORNO:
        VideoAnalysisResponse: Desglose con categoría temática, estética visual,
                               tono emocional y aprendizajes clave.
    """
    # 1. Comprobamos la disponibilidad de una clave válida de Gemini
    api_key = get_gemini_api_key(req.api_key)

    # Si no hay clave, ejecutamos el analizador heurístico de respaldo
    if not api_key:
        return _analyze_video_heuristic(req)

    # 2. Importación diferida del SDK de Gemini
    from google import genai
    from google.genai import types

    # Muestra representativa de hasta 8 comentarios para que la IA comprenda la reacción del público
    comments_sample = "\n- ".join(req.comments[:8]) if req.comments else "No hay comentarios disponibles."

    # 3. DESCARGA ASÍNCRONA DE LA MINIATURA / PORTADA MULTIMODAL:
    image_part = None
    if req.cover_url:
        try:
            # Descargamos los bytes de la imagen con timeout de 10 segundos
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                img_res = await client.get(req.cover_url)
                if img_res.status_code == 200:
                    content_type = img_res.headers.get("content-type", "image/jpeg").split(";")[0]
                    # Construimos la parte multimodal binaria compatible con Gemini
                    image_part = types.Part.from_bytes(
                        data=img_res.content,
                        mime_type=content_type
                    )
        except Exception as e:
            logger.warning(f"No se pudo descargar la miniatura del video {req.video_id}: {e}")

    # 4. PROMPT ESPECIALIZADO EN ANÁLISIS DE CONTENIDO VERTICAL:
    prompt = f"""
Eres un analista de contenido digital y psicología de redes sociales.
Analiza este video de TikTok:

ID: {req.video_id}
URL: {req.url}
Descripción: {req.description or 'Sin descripción'}

Comentarios de la audiencia:
- {comments_sample}

TAREA:
Proporciona un desglose analítico del video:
1. Categoría temática del video.
2. Estilo visual y de producción (analizando la imagen/miniatura si está adjunta y el formato).
3. Tono emocional proyectado en el contenido.
4. Reacción e impacto en la audiencia.
5. Indicios de personalidad del creador (Apertura, Responsabilidad, Extraversión, etc.).
6. 3 aprendizajes o conclusiones clave.

Devuelve EXCLUSIVAMENTE un JSON con esta estructura exacta:
{{
  "topic_category": "Educación / Comedia / Lifestyle / etc.",
  "visual_and_production_style": "Descripción del encuadre, estética, ritmo y dinamismo visual.",
  "emotional_tone": "Humorístico, inspirador, reflexivo, etc.",
  "audience_reaction": "Resumen de cómo reaccionaron los usuarios en los comentarios.",
  "personality_cues": {{
    "Extraversion": "Indicadores observados en este video",
    "Openness": "Indicadores de creatividad o enfoque novedoso",
    "Agreeableness": "Cercanía o empatía con los espectadores"
  }},
  "key_takeaways": [
    "Punto clave 1",
    "Punto clave 2",
    "Punto clave 3"
  ]
}}
"""

    client = genai.Client(api_key=api_key)
    
    # Creamos el contenedor de contenidos: texto + imagen (si se descargó exitosamente)
    contents = [prompt]
    if image_part:
        contents.append(image_part)

    # 5. INFERENCIA CON GESTIÓN DE FALLBACK DE MODELOS:
    response, used_model = generate_content_with_fallback(
        client=client,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
        preferred_model=DEFAULT_GEMINI_MODEL
    )

    res_text = response.text.strip()
    # Limpieza preventiva de bloques markdown ```json
    if res_text.startswith("```"):
        res_text = re.sub(r"^```(?:json)?\n?", "", res_text)
        res_text = re.sub(r"\n?```$", "", res_text)

    data = json.loads(res_text)

    # 6. Retorno de la respuesta validada con Pydantic
    return VideoAnalysisResponse(
        video_id=req.video_id,
        topic_category=data.get("topic_category", "General"),
        visual_and_production_style=data.get("visual_and_production_style", "Formato vertical dinámico típico de TikTok."),
        emotional_tone=data.get("emotional_tone", "Neutro"),
        audience_reaction=data.get("audience_reaction", "Interacción estándar de la comunidad."),
        personality_cues=data.get("personality_cues", {}),
        key_takeaways=data.get("key_takeaways", []),
        model_used=f"Google Gemini AI ({used_model})"
    )


# ==============================================================================
# 3. ANÁLISIS HEURÍSTICO LOCAL DE RESPALDO (SIN API KEY)
# ==============================================================================

def _analyze_video_heuristic(req: VideoAnalysisRequest) -> VideoAnalysisResponse:
    """
    Genera un informe semántico local y contextual en caso de no disponer de API Key.

    ¿POR QUÉ EXISTE?:
        Permite al usuario presionar '✨ Analizar Video con IA' en la interfaz
        y recibir un desglose coherente basado en palabras clave y métricas
        sin experimentar cuelgues ni errores de servidor.
    """
    desc = (req.description or "").lower()
    comments_str = " ".join(req.comments).lower()

    # Clasificación temática basada en vocabulario contextual
    if any(k in desc for k in ["tutorial", "aprende", "como", "tips", "hacks", "guia"]):
        category = "Educativo / Tutorial"
    elif any(k in desc for k in ["humor", "risa", "meme", "broma", "pov", "jaja"]):
        category = "Comedia y Entretenimiento"
    elif any(k in desc for k in ["fit", "gym", "rutina", "salud", "comida", "dieta"]):
        category = "Fitness y Salud"
    elif any(k in desc for k in ["vlog", "dia", "conmigo", "viaje", "experiencia"]):
        category = "Lifestyle / Vlogging"
    else:
        category = "Contenido General / Opinión"

    # Inferencia del tono emocional
    if any(k in desc or k in comments_str for k in ["increible", "genial", "top", "gracias"]):
        tone = "Inspirador y Positivo"
    elif any(k in desc or k in comments_str for k in ["alerta", "cuidado", "secreto", "ojo"]):
        tone = "Urgente / Revelador"
    else:
        tone = "Conversacional y Cercano"

    return VideoAnalysisResponse(
        video_id=req.video_id,
        topic_category=category,
        visual_and_production_style="Formato nativo de TikTok optimizado para alta retención de audiencia.",
        emotional_tone=tone,
        audience_reaction=f"Comentarios centrados en la temática ({len(req.comments)} comentarios analizados).",
        personality_cues={
            "Extraversion": "Fuerte capacidad de proyección y llamado a la acción.",
            "Openness": "Creatividad en la síntesis del mensaje corto.",
            "Conscientiousness": "Claridad en el mensaje y uso de hashtags pertinentes."
        },
        key_takeaways=[
            "Alta relevancia temática para la comunidad de este creador.",
            "Estructura orientada a generar interacción y retención en el feed 'Para Ti'.",
            "Configura GEMINI_API_KEY para desbloquear el análisis de fotogramas e inteligencia multimodal."
        ],
        model_used="Heurístico (Sin API Key)"
    )
