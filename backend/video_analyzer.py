import json
import logging
import re
from typing import Optional, List
import httpx
from backend.models import VideoAnalysisRequest, VideoAnalysisResponse
from backend.config import get_gemini_api_key, DEFAULT_GEMINI_MODEL

logger = logging.getLogger("scrappy.video_analyzer")


async def analyze_single_video(req: VideoAnalysisRequest) -> VideoAnalysisResponse:
    """
    Analiza un video específico de TikTok:
    - Si hay API Key de Gemini: analiza multimodalmente la miniatura/portada del video,
      la narrativa, tono, recepción del público y rasgos proyectados.
    - Si no hay API Key: genera un análisis semántico y métrico contextual de respaldo.
    """
    api_key = get_gemini_api_key(req.api_key)

    if not api_key:
        return _analyze_video_heuristic(req)

    from google import genai
    from google.genai import types

    comments_sample = "\n- ".join(req.comments[:8]) if req.comments else "No hay comentarios disponibles."

    # Intentar descargar la imagen de portada/miniatura para análisis multimodal
    image_part = None
    if req.cover_url:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                img_res = await client.get(req.cover_url)
                if img_res.status_code == 200:
                    content_type = img_res.headers.get("content-type", "image/jpeg").split(";")[0]
                    image_part = types.Part.from_bytes(
                        data=img_res.content,
                        mime_type=content_type
                    )
        except Exception as e:
            logger.warning(f"No se pudo descargar la miniatura del video {req.video_id}: {e}")

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
    contents = [prompt]
    if image_part:
        contents.append(image_part)

    model_name = DEFAULT_GEMINI_MODEL
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            )
        )
    except Exception as e:
        logger.warning(f"Error con modelo {model_name} en video: {e}. Reintentando con gemini-1.5-flash")
        model_name = "gemini-1.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            )
        )

    res_text = response.text.strip()
    if res_text.startswith("```"):
        res_text = re.sub(r"^```(?:json)?\n?", "", res_text)
        res_text = re.sub(r"\n?```$", "", res_text)

    data = json.loads(res_text)

    return VideoAnalysisResponse(
        video_id=req.video_id,
        topic_category=data.get("topic_category", "General"),
        visual_and_production_style=data.get("visual_and_production_style", "Formato vertical dinámico típico de TikTok."),
        emotional_tone=data.get("emotional_tone", "Neutro"),
        audience_reaction=data.get("audience_reaction", "Interacción estándar de la comunidad."),
        personality_cues=data.get("personality_cues", {}),
        key_takeaways=data.get("key_takeaways", []),
        model_used=f"Google Gemini AI ({model_name})"
    )


def _analyze_video_heuristic(req: VideoAnalysisRequest) -> VideoAnalysisResponse:
    """
    Análisis heurístico de respaldo cuando no hay Gemini API Key configurada.
    """
    desc = (req.description or "").lower()
    comments_str = " ".join(req.comments).lower()

    # Detectar categoría por palabras clave
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

    # Tono emocional
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
