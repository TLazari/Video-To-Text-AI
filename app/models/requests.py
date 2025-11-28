"""
Modelos de requisição para a API de análise de vídeos
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class AnalysisDepth(str, Enum):
    """Profundidade da análise"""
    QUICK = "quick"          # Análise rápida, menos detalhada
    STANDARD = "standard"    # Análise padrão
    DETAILED = "detailed"    # Análise muito detalhada


class AnalysisOptions(BaseModel):
    """Opções de análise do vídeo"""
    analysis_depth: AnalysisDepth = Field(
        default=AnalysisDepth.STANDARD,
        description="Profundidade da análise"
    )
    include_timestamps: bool = Field(
        default=True,
        description="Incluir timestamps de momentos-chave"
    )
    language: str = Field(
        default="pt-BR",
        description="Idioma da análise",
        pattern="^[a-z]{2}-[A-Z]{2}$"
    )
    extract_entities: bool = Field(
        default=False,
        description="Extrair entidades (pessoas, objetos, locais)"
    )
    detect_sentiment: bool = Field(
        default=False,
        description="Detectar sentimento/tom do vídeo"
    )


class VideoAnalysisRequest(BaseModel):
    """Requisição de análise de vídeo"""
    video_url: str = Field(
        ...,
        description="URL HTTP do vídeo (http://localhost:8000/videos/sample.mp4 ou URL remota)",
        min_length=1,
        examples=["http://localhost:8000/videos/sample.mp4"]
    )
    options: Optional[AnalysisOptions] = Field(
        default_factory=AnalysisOptions,
        description="Opções de análise automática (ignorado se custom_prompt for fornecido). Define profundidade, idioma, entidades, sentimento, etc."
    )
    custom_prompt: Optional[str] = Field(
        default=None,
        description="[OPCIONAL] Prompt customizado para análise do vídeo (sobrescreve as opções). Use quando quiser controle total sobre as instruções de análise. Se não fornecido, usa as opções automáticas. Exemplo: 'Analise e forneça: 1) Resumo, 2) Tópicos em bullet points, 3) Conclusão'",
        examples=[
            "Analise este vídeo e identifique os principais tópicos discutidos",
            "Forneça: 1) Resumo em 3 frases, 2) Tópicos em bullet points, 3) Conclusão"
        ]
    )

    @field_validator('video_url')
    @classmethod
    def validate_video_url(cls, v: str) -> str:
        """Valida formato básico da URL"""
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL deve usar protocolo HTTP ou HTTPS (ex: http://localhost:8000/videos/sample.mp4)")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "video_url": "http://localhost:8000/videos/presentation.mp4",
                    "options": {
                        "analysis_depth": "detailed",
                        "include_timestamps": True,
                        "language": "pt-BR",
                        "extract_entities": True,
                        "detect_sentiment": True
                    }
                },
                {
                    "video_url": "http://localhost:8000/videos/presentation.mp4",
                    "custom_prompt": "Analise os principais tópicos, identifique as pessoas presentes e liste as conclusões em formato bullet points"
                }
            ]
        }
    }
