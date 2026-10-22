import json
import logging
import re
from typing import Dict, Any, List
from backend.models import (
    BigFiveAnalysis,
    BigFiveTrait,
    SentimentAnalysis,
    SentimentBreakdown,
    ProfileData,
)
from backend.config import get_gemini_api_key, DEFAULT_GEMINI_MODEL

logger = logging.getLogger("scrappy.analyzer")

# Modelos candidatos de Gemini en orden de prioridad para fallback automático
CANDIDATE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-pro-latest"
]

_cached_working_model: str | None = None


def generate_content_with_fallback(client, contents, config=None, preferred_model: str | None = None):
    """
    Intenta generar contenido probando modelos compatibles de Gemini.
    Si un modelo responde 404 (no encontrado / retirado) o 503 (alta demanda),
    prueba automáticamente los siguientes candidatos compatibles.
    """
    global _cached_working_model

    models_to_try = []
    if _cached_working_model and _cached_working_model not in models_to_try:
        models_to_try.append(_cached_working_model)
    if preferred_model and preferred_model not in models_to_try:
        models_to_try.append(preferred_model)
    if DEFAULT_GEMINI_MODEL and DEFAULT_GEMINI_MODEL not in models_to_try:
        models_to_try.append(DEFAULT_GEMINI_MODEL)

    for cand in CANDIDATE_MODELS:
        if cand not in models_to_try:
            models_to_try.append(cand)

    last_error = None
    for model_name in models_to_try:
        try:
            logger.info(f"Probando llamada con modelo Gemini: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            _cached_working_model = model_name
            return response, model_name
        except Exception as e:
            err_str = str(e)
            logger.warning(f"Aviso con modelo {model_name}: {err_str[:90]}")
            last_error = e
            # Continuar con el siguiente candidato si este falló
            continue

    if last_error:
        raise last_error
    raise RuntimeError("No se encontró ningún modelo de Gemini disponible para la clave proporcionada.")

# Lexicon básico bilingüe (Español / Inglés) para análisis heurístico de respaldo
POSITIVE_WORDS = {
    "excelente", "bueno", "increible", "genial", "amor", "feliz", "gracias",
    "top", "crack", "bello", "hermoso", "exito", "motivacion", "aprendizaje",
    "inspiracion", "alegria", "pasion", "orgullo", "triunfo", "arte",
    "good", "great", "awesome", "love", "happy", "thanks", "best", "cool",
    "fire", "pro", "master", "wins", "blessed", "creative", "amazing"
}

NEGATIVE_WORDS = {
    "mal", "malo", "horrible", "pesimo", "odio", "triste", "estres", "enojo",
    "rabia", "asco", "aburrido", "estafa", "mentira", "falso", "problema",
    "queja", "critica", "decepcion", "miedo", "fracaso", "toxico",
    "bad", "terrible", "hate", "sad", "anger", "boring", "fake", "scam",
    "fail", "loss", "toxic", "problem", "cringe", "worst", "stress"
}

OPENNESS_KEYWORDS = {
    "innovar", "crear", "arte", "diseno", "idea", "aprender", "futuro", "filosofia",
    "curiosidad", "viajar", "nueva", "nuevo", "descubrir", "magia", "ciencia", "historia",
    "create", "art", "design", "future", "mind", "curious", "explore", "learn", "ideas"
}

SOCIAL_ENGAGEMENT_WORDS = {
    "ustedes", "amigos", "comunidad", "comenta", "comparte", "cuentenme", "opinen",
    "juntos", "familia", "equipo", "gente", "chicos", "seguidores",
    "community", "share", "comment", "tell me", "friends", "together", "guys", "we"
}


def analyze_heuristic(profile: ProfileData) -> BigFiveAnalysis:
    """
    Analizador heurístico basado en lingüística, métricas de engagement y semántica.
    Se ejecuta si no se cuenta con una API Key de Gemini o en caso de fallo de red.
    """
    all_text = (profile.bio or "") + " "
    for v in profile.videos:
        all_text += (v.description or "") + " "
        all_text += " ".join(v.comments_list) + " "

    tokens = re.findall(r"\b\w+\b", all_text.lower())
    token_count = max(len(tokens), 1)

    # Conteo de sentimientos
    pos_count = sum(1 for w in tokens if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in tokens if w in NEGATIVE_WORDS)
    total_sentiment_words = pos_count + neg_count

    if total_sentiment_words > 0:
        pos_pct = int(round((pos_count / (total_sentiment_words + 5)) * 100))
        neg_pct = int(round((neg_count / (total_sentiment_words + 5)) * 100))
        neu_pct = max(0, 100 - (pos_pct + neg_pct))
    else:
        pos_pct, neu_pct, neg_pct = 50, 40, 10

    sentiment_score = round((pos_count - neg_count) / max(total_sentiment_words, 1), 2)
    overall_sentiment = (
        "Positivo" if sentiment_score > 0.25 else
        "Mayormente Positivo" if sentiment_score > 0.05 else
        "Neutro / Informativo" if sentiment_score >= -0.1 else
        "Crítico / Controversial"
    )

    # 1. Apertura a la Experiencia (Openness)
    openness_matches = sum(1 for w in tokens if w in OPENNESS_KEYWORDS)
    desc_lengths = [len(v.description.split()) for v in profile.videos]
    avg_desc_len = sum(desc_lengths) / max(len(desc_lengths), 1)
    openness_score = int(min(95, max(35, 45 + (openness_matches * 5) + (avg_desc_len * 0.8))))

    # 2. Responsabilidad (Conscientiousness)
    # Calidad de hashtags, uso de puntuación ordenada, estructura
    has_hashtags = sum(1 for v in profile.videos if "#" in v.description)
    structured_ratio = (has_hashtags / max(len(profile.videos), 1))
    conscientiousness_score = int(min(92, max(40, 50 + int(structured_ratio * 30))))

    # 3. Extraversión (Extraversion)
    social_words_count = sum(1 for w in tokens if w in SOCIAL_ENGAGEMENT_WORDS)
    exclamations = all_text.count("!") + all_text.count("¡")
    questions = all_text.count("?") + all_text.count("¿")
    extraversion_score = int(min(96, max(30, 48 + (social_words_count * 4) + (exclamations * 2) + (questions * 2))))

    # 4. Amabilidad (Agreeableness)
    agreeableness_score = int(min(94, max(35, 52 + (pos_pct * 0.35) - (neg_pct * 0.4))))

    # 5. Neuroticismo / Reactividad Emocional (Neuroticism)
    # Mayor presencia de palabras negativas o intensidad dramática
    neuroticism_score = int(min(85, max(20, 28 + (neg_pct * 0.6) + int(exclamations * 0.8))))

    def get_level(score: int) -> str:
        if score >= 68:
            return "Alto"
        elif score >= 45:
            return "Medio"
        return "Bajo"

    return BigFiveAnalysis(
        openness=BigFiveTrait(
            score=openness_score,
            level=get_level(openness_score),
            summary="Capacidad creativa, interés en nuevos temas y estilo narrativo.",
            characteristics=["Variedad temática en los videos", "Uso de vocabulario descriptivo", "Curiosidad intelectual"]
        ),
        conscientiousness=BigFiveTrait(
            score=conscientiousness_score,
            level=get_level(conscientiousness_score),
            summary="Disciplina en la publicación, estructura de descripciones y coherencia.",
            characteristics=["Consistencia en la estructura de posts", "Enfoque en objetivos de contenido", "Organización en hashtags"]
        ),
        extraversion=BigFiveTrait(
            score=extraversion_score,
            level=get_level(extraversion_score),
            summary="Nivel de interacción social, energía proyectada y dinamismo hacia la comunidad.",
            characteristics=["Llamados a la acción para comentar", "Uso de signos expresivos y dinamismo", "Conexión directa con la audiencia"]
        ),
        agreeableness=BigFiveTrait(
            score=agreeableness_score,
            level=get_level(agreeableness_score),
            summary="Calidez, tono empático y apertura hacia las opiniones de los seguidores.",
            characteristics=["Tono cercano y colaborativo", "Respuestas constructivas", "Ambiente positivo de interacción"]
        ),
        neuroticism=BigFiveTrait(
            score=neuroticism_score,
            level=get_level(neuroticism_score),
            summary="Estabilidad emocional, serenidad ante críticas y manejo de la presión.",
            characteristics=["Tono templado y seguro", "Baja reactividad ante controversias", "Autocontrol en sus expresiones"]
        ),
        general_summary=(
            f"El perfil @{profile.username} proyecta una personalidad con marcada tendencia a "
            f"{get_level(extraversion_score).lower()} en extraversión y {get_level(openness_score).lower()} en apertura. "
            f"Su contenido mantiene un enfoque {overall_sentiment.lower()} y una comunicación estructurada."
        ),
        communication_style="Directo, dinámico y enfocado en generar conexión con su audiencia en TikTok.",
        key_strengths=[
            "Alta capacidad para enganchar con temas variados",
            "Manejo fluido del tono coloquial y persuasivo",
            "Buena recepción y retroalimentación de la comunidad"
        ],
        sentiment=SentimentAnalysis(
            overall=overall_sentiment,
            score=sentiment_score,
            breakdown=SentimentBreakdown(
                positive=pos_pct,
                neutral=neu_pct,
                negative=neg_pct
            ),
            dominant_emotions=["Entusiasmo", "Cercanía", "Curiosidad"],
            community_tone="Participativo y receptivo hacia el creador"
        ),
        model_used="Análisis Heurístico / NLP (Configura GEMINI_API_KEY para LLM multimodal)"
    )


def analyze_with_gemini(profile: ProfileData, api_key: str) -> BigFiveAnalysis:
    """
    Analizador profundo de los rasgos Big Five (OCEAN) y Sentimiento usando la API de Google Gemini.
    """
    from google import genai
    from google.genai import types

    # Resumen de videos y comentarios para el prompt
    videos_summary = []
    for i, v in enumerate(profile.videos[:10], start=1):
        comments_preview = " | ".join(v.comments_list[:5]) if v.comments_list else "Sin comentarios"
        videos_summary.append(
            f"Video #{i}: '{v.description}' (Likes: {v.likes}, Comentarios: {v.comments_count}, Compartidos: {v.shares})\n"
            f"  Comentarios destacados: {comments_preview}"
        )

    content_text = "\n".join(videos_summary)

    prompt = f"""
Eres un psicólogo de la personalidad y experto en análisis de redes sociales (Big Five Personality Model - OCEAN).
Analiza el siguiente perfil extraído de TikTok:

Perfil: @{profile.username}
Nombre: {profile.name}
Seguidores: {profile.followers} | Seguidos: {profile.following}
Biografía: {profile.bio or 'No especificada'}

Muestra de los últimos 10 videos extraídos y comentarios de su comunidad:
{content_text}

TAREA:
Evalúa los 5 rasgos de personalidad del modelo Big Five (OCEAN) para este creador de contenido, junto con un análisis de sentimiento integral:
1. Openness (Apertura a la experiencia): curiosidad, originalidad artística, diversidad temática. (0-100)
2. Conscientiousness (Responsabilidad / Escrupulosidad): disciplina, estructura, consistencia en formato y objetivos. (0-100)
3. Extraversion (Extraversión): energía social, asertividad, búsqueda de atención y calidez hacia el público. (0-100)
4. Agreeableness (Amabilidad / Afabilidad): empatía, cooperación, tono inclusivo, tolerancia. (0-100)
5. Neuroticism (Neuroticismo / Reactividad Emocional): sensibilidad al estrés, tono ansioso/dramático o serenidad. (0-100)

Devuelve ÚNICAMENTE un objeto JSON válido con este formato exacto:
{{
  "openness": {{
    "score": 75,
    "level": "Alto",
    "summary": "Explicación concisa",
    "characteristics": ["Punto 1", "Punto 2"]
  }},
  "conscientiousness": {{
    "score": 68,
    "level": "Medio",
    "summary": "Explicación concisa",
    "characteristics": ["Punto 1", "Punto 2"]
  }},
  "extraversion": {{
    "score": 82,
    "level": "Alto",
    "summary": "Explicación concisa",
    "characteristics": ["Punto 1", "Punto 2"]
  }},
  "agreeableness": {{
    "score": 70,
    "level": "Alto",
    "summary": "Explicación concisa",
    "characteristics": ["Punto 1", "Punto 2"]
  }},
  "neuroticism": {{
    "score": 35,
    "level": "Bajo",
    "summary": "Explicación concisa",
    "characteristics": ["Punto 1", "Punto 2"]
  }},
  "general_summary": "Párrafo completo y bien redactado resumiendo el perfil psicológico y de creador.",
  "communication_style": "Descripción del tono y estilo de comunicación con la audiencia.",
  "key_strengths": ["Fortaleza 1", "Fortaleza 2", "Fortaleza 3"],
  "sentiment": {{
    "overall": "Positivo",
    "score": 0.65,
    "breakdown": {{
      "positive": 70,
      "neutral": 20,
      "negative": 10
    }},
    "dominant_emotions": ["Inspiración", "Entusiasmo", "Alegría"],
    "community_tone": "Descripción del ambiente de los comentarios recibidos"
  }}
}}
"""

    client = genai.Client(api_key=api_key)

    response, used_model = generate_content_with_fallback(
        client=client,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
        preferred_model=DEFAULT_GEMINI_MODEL
    )

    response_text = response.text.strip()
    # Limpieza preventiva en caso de que venga con bloques markdown ```json
    if response_text.startswith("```"):
        response_text = re.sub(r"^```(?:json)?\n?", "", response_text)
        response_text = re.sub(r"\n?```$", "", response_text)

    data = json.loads(response_text)

    return BigFiveAnalysis(
        openness=BigFiveTrait(**data["openness"]),
        conscientiousness=BigFiveTrait(**data["conscientiousness"]),
        extraversion=BigFiveTrait(**data["extraversion"]),
        agreeableness=BigFiveTrait(**data["agreeableness"]),
        neuroticism=BigFiveTrait(**data["neuroticism"]),
        general_summary=data["general_summary"],
        communication_style=data["communication_style"],
        key_strengths=data.get("key_strengths", []),
        sentiment=SentimentAnalysis(
            overall=data["sentiment"]["overall"],
            score=float(data["sentiment"]["score"]),
            breakdown=SentimentBreakdown(**data["sentiment"]["breakdown"]),
            dominant_emotions=data["sentiment"].get("dominant_emotions", []),
            community_tone=data["sentiment"].get("community_tone", "")
        ),
        model_used=f"Google Gemini AI ({used_model})"
    )


def perform_bigfive_analysis(profile: ProfileData, override_api_key: str | None = None) -> BigFiveAnalysis:
    """
    Función principal que coordina el análisis de Big Five y Sentimiento:
    Usa Gemini si la API Key está disponible; de lo contrario, recurre al analizador heurístico.
    """
    api_key = get_gemini_api_key(override_api_key)

    if api_key:
        try:
            logger.info("Ejecutando análisis Big Five con Gemini AI...")
            return analyze_with_gemini(profile, api_key)
        except Exception as e:
            logger.error(f"Fallo al conectar con Gemini AI ({e}). Usando analizador heurístico de respaldo.")
            fallback = analyze_heuristic(profile)
            fallback.model_used = f"Heurístico (Fallo de Gemini API: {str(e)[:60]}...)"
            return fallback
    else:
        logger.info("No se detectó GEMINI_API_KEY. Ejecutando análisis heurístico...")
        return analyze_heuristic(profile)
