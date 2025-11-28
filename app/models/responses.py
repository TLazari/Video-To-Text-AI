"""
Modelos de resposta para a API de análise de vídeos
"""
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    """Status do job de processamento"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorCode(str, Enum):
    """Códigos de erro"""
    INVALID_VIDEO_URL = "INVALID_VIDEO_URL"
    VIDEO_NOT_FOUND = "VIDEO_NOT_FOUND"
    VIDEO_TOO_LARGE = "VIDEO_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    VIDEO_PROCESSING_ERROR = "VIDEO_PROCESSING_ERROR"
    OPENROUTER_API_ERROR = "OPENROUTER_API_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class Links(BaseModel):
    """Links HATEOAS"""
    self: str = Field(..., description="Link para o próprio recurso")
    status: str = Field(..., description="Link para consulta de status")
    cancel: Optional[str] = Field(None, description="Link para cancelar job (se aplicável)")


class VideoMetadata(BaseModel):
    """Metadados do vídeo"""
    duration_seconds: float = Field(..., description="Duração em segundos")
    resolution: str = Field(..., description="Resolução (ex: 1920x1080)")
    format: str = Field(..., description="Formato do vídeo (ex: mp4)")
    size_bytes: int = Field(..., description="Tamanho do arquivo em bytes")
    fps: Optional[float] = Field(None, description="Frames por segundo")
    codec: Optional[str] = Field(None, description="Codec de vídeo")


class KeyMoment(BaseModel):
    """Momento-chave no vídeo"""
    timestamp: str = Field(..., description="Timestamp (MM:SS ou HH:MM:SS)")
    description: str = Field(..., description="Descrição do momento")
    importance: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Importância do momento"
    )


class Entity(BaseModel):
    """Entidade detectada no vídeo"""
    type: Literal["person", "object", "location", "brand"] = Field(
        ...,
        description="Tipo da entidade"
    )
    name: str = Field(..., description="Nome da entidade")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confiança da detecção (0.0 - 1.0)"
    )


class AnalysisMetadata(BaseModel):
    """Metadados da análise"""
    language_detected: Optional[str] = Field(None, description="Idioma detectado")
    topics: List[str] = Field(default_factory=list, description="Tópicos/categorias")
    sentiment: Optional[Literal["positive", "neutral", "negative"]] = Field(
        None,
        description="Sentimento geral"
    )
    key_moments: Optional[List[KeyMoment]] = Field(
        default_factory=list,
        description="Momentos-chave"
    )
    entities: Optional[List[Entity]] = Field(
        default_factory=list,
        description="Entidades detectadas"
    )


class Analysis(BaseModel):
    """Análise do vídeo"""
    markdown: str = Field(..., description="Análise completa em Markdown")
    summary: str = Field(..., description="Resumo curto em texto plano")
    metadata: AnalysisMetadata = Field(..., description="Metadados da análise")


class AIProviderInfo(BaseModel):
    """Informações do provedor de IA"""
    provider: str = Field(default="openrouter", description="Provedor de IA")
    model: str = Field(..., description="Modelo utilizado")
    tokens_used: int = Field(..., description="Tokens utilizados")
    cost_usd: Optional[float] = Field(None, description="Custo em USD")
    processing_time_ms: int = Field(..., description="Tempo de processamento em ms")


class AnalysisResult(BaseModel):
    """Resultado completo da análise"""
    video_metadata: VideoMetadata = Field(..., description="Metadados do vídeo")
    analysis: Analysis = Field(..., description="Análise do vídeo")
    ai_provider: AIProviderInfo = Field(..., description="Informações do provedor de IA")


class ProgressInfo(BaseModel):
    """Informações de progresso"""
    current_step: str = Field(..., description="Etapa atual")
    percentage: int = Field(..., ge=0, le=100, description="Percentual de conclusão")
    message: str = Field(..., description="Mensagem de status")


class ErrorInfo(BaseModel):
    """Informações de erro"""
    code: ErrorCode = Field(..., description="Código do erro")
    message: str = Field(..., description="Mensagem de erro")
    details: Optional[str] = Field(None, description="Detalhes adicionais")
    retry_after: Optional[int] = Field(
        None,
        description="Segundos até retry ser possível"
    )


class VideoAnalysisResponse(BaseModel):
    """Resposta de análise de vídeo"""
    job_id: str = Field(..., description="UUID do job")
    status: JobStatus = Field(..., description="Status do processamento")
    created_at: datetime = Field(..., description="Data/hora de criação")
    updated_at: Optional[datetime] = Field(None, description="Data/hora de atualização")
    completed_at: Optional[datetime] = Field(None, description="Data/hora de conclusão")
    processing_time_seconds: Optional[float] = Field(
        None,
        description="Tempo total de processamento"
    )
    estimated_time_seconds: Optional[int] = Field(
        None,
        description="Tempo estimado (apenas quando pending)"
    )
    result: Optional[AnalysisResult] = Field(None, description="Resultado da análise")
    progress: Optional[ProgressInfo] = Field(None, description="Informações de progresso")
    error: Optional[ErrorInfo] = Field(None, description="Informações de erro")
    _links: Links = Field(..., description="Links HATEOAS")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "completed",
                    "created_at": "2025-11-28T10:30:00Z",
                    "completed_at": "2025-11-28T10:32:30Z",
                    "processing_time_seconds": 150.5,
                    "result": {
                        "video_metadata": {
                            "duration_seconds": 180.0,
                            "resolution": "1920x1080",
                            "format": "mp4",
                            "size_bytes": 45000000,
                            "fps": 30.0,
                            "codec": "h264"
                        },
                        "analysis": {
                            "markdown": "# Análise do Vídeo\n\n## Resumo\n\nVídeo tutorial...",
                            "summary": "Vídeo tutorial sobre programação Python",
                            "metadata": {
                                "language_detected": "pt-BR",
                                "topics": ["tecnologia", "programação", "python"],
                                "sentiment": "positive",
                                "key_moments": [
                                    {
                                        "timestamp": "00:15",
                                        "description": "Introdução do instrutor",
                                        "importance": "high"
                                    }
                                ]
                            }
                        },
                        "ai_provider": {
                            "provider": "openrouter",
                            "model": "openai/gpt-4-vision-preview",
                            "tokens_used": 1500,
                            "processing_time_ms": 3200
                        }
                    },
                    "_links": {
                        "self": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
                        "status": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/status"
                    }
                }
            ]
        }
    }


class JobSubmittedResponse(BaseModel):
    """Resposta de job submetido (HTTP 202)"""
    job_id: str = Field(..., description="UUID do job")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Status inicial")
    created_at: datetime = Field(..., description="Data/hora de criação")
    estimated_time_seconds: int = Field(..., description="Tempo estimado de processamento")
    _links: Links = Field(..., description="Links HATEOAS")
