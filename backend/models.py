from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class VideoData(BaseModel):
    video_id: str
    url: str
    description: str = ""
    likes: int = 0
    comments_count: int = 0
    saves: int = 0
    shares: int = 0
    comments_list: List[str] = Field(default_factory=list)
    cover_url: Optional[str] = None
    duration: Optional[int] = 0
    create_time: Optional[int] = None


class BigFiveTrait(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Puntuación de 0 a 100")
    level: str = Field(..., description="Alto, Medio o Bajo")
    summary: str = Field(..., description="Breve explicación del rasgo en este creador")
    characteristics: List[str] = Field(default_factory=list, description="Puntos clave observados")


class SentimentBreakdown(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0


class SentimentAnalysis(BaseModel):
    overall: str = "Neutro"  # Positivo, Neutro, Crítico, Inspirador, etc.
    score: float = 0.0       # Escala de -1.0 a +1.0
    breakdown: SentimentBreakdown = Field(default_factory=SentimentBreakdown)
    dominant_emotions: List[str] = Field(default_factory=list)
    community_tone: str = ""


class BigFiveAnalysis(BaseModel):
    openness: BigFiveTrait
    conscientiousness: BigFiveTrait
    extraversion: BigFiveTrait
    agreeableness: BigFiveTrait
    neuroticism: BigFiveTrait
    general_summary: str
    communication_style: str
    key_strengths: List[str] = Field(default_factory=list)
    sentiment: SentimentAnalysis
    model_used: str = "Gemini AI"


class ProfileData(BaseModel):
    username: str
    name: str = ""
    followers: int = 0
    following: int = 0
    bio: Optional[str] = ""
    avatar_url: Optional[str] = None
    videos: List[VideoData] = Field(default_factory=list)
    analysis: Optional[BigFiveAnalysis] = None


class VideoAnalysisRequest(BaseModel):
    video_id: str
    url: str
    description: str = ""
    comments: List[str] = Field(default_factory=list)
    cover_url: Optional[str] = None
    api_key: Optional[str] = None


class VideoAnalysisResponse(BaseModel):
    video_id: str
    topic_category: str
    visual_and_production_style: str
    emotional_tone: str
    audience_reaction: str
    personality_cues: Dict[str, str] = Field(default_factory=dict)
    key_takeaways: List[str] = Field(default_factory=list)
    model_used: str = "Gemini AI"
