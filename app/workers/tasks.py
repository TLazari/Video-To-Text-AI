"""
Tasks do Celery para processamento de vídeos
"""
import asyncio
import json
from datetime import datetime
import structlog
import redis

from app.workers.celery_app import celery_app
from app.config import settings
from app.services.video_processor import VideoProcessorService
from app.services.openrouter_client import OpenRouterClient
from app.models.responses import (
    JobStatus,
    VideoMetadata,
    AnalysisMetadata,
    Analysis,
    AIProviderInfo,
    AnalysisResult,
    VideoAnalysisResponse,
    Links,
)
from app.core.exceptions import VideoAPIException

logger = structlog.get_logger(__name__)

# Cliente Redis para armazenar resultados
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)


@celery_app.task(
    bind=True,
    name="analyze_video",
    max_retries=3,
    default_retry_delay=60
)
def analyze_video(self, job_id: str, request_data: dict):
    """
    Task para análise de vídeo em background

    Args:
        self: Self do Celery task
        job_id: ID único do job
        request_data: Dados da requisição (video_url, options, etc)

    Returns:
        Resultado da análise ou erro
    """
    start_time = datetime.utcnow()
    logger.info("Starting video analysis task", job_id=job_id, video_url=request_data.get("video_url"))

    # Atualiza status para "processing"
    _update_job_status(job_id, JobStatus.PROCESSING)

    try:
        # Roda async code em event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _analyze_video_async(job_id, request_data)
            )
        finally:
            loop.close()

        # Armazena resultado no Redis
        _store_result(job_id, result)

        logger.info("Video analysis completed", job_id=job_id)
        return result

    except VideoAPIException as e:
        logger.error(
            "Video processing failed",
            job_id=job_id,
            error=str(e),
            error_code=e.error_code
        )
        _store_error(job_id, str(e), e.error_code)
        return {"error": str(e), "error_code": e.error_code}

    except Exception as e:
        logger.error(
            "Unexpected error in video analysis",
            job_id=job_id,
            error=str(e)
        )
        _store_error(job_id, str(e), "INTERNAL_ERROR")
        return {"error": str(e), "error_code": "INTERNAL_ERROR"}


async def _analyze_video_async(job_id: str, request_data: dict) -> dict:
    """
    Implementação assíncrona da análise de vídeo

    Args:
        job_id: ID do job
        request_data: Dados da requisição

    Returns:
        Resultado completo da análise
    """
    video_url = request_data["video_url"]
    options = request_data.get("options", {})

    logger.info("Analyzing video", job_id=job_id, video_url=video_url)

    # 1. Valida vídeo
    video_info = await VideoProcessorService.validate_video(video_url)

    # 2. Extrai metadados do vídeo
    video_metadata_dict = await VideoProcessorService.extract_metadata(video_url)

    # Formata para o schema
    video_metadata = VideoMetadata(
        duration_seconds=video_metadata_dict["duration_seconds"],
        resolution=video_metadata_dict["resolution"],
        format=video_info["format"],
        size_bytes=int(video_info["size_mb"] * 1024 * 1024),
        fps=video_metadata_dict["fps"],
        codec=video_metadata_dict["codec"]
    )

    # 3. Prepara cliente OpenRouter
    openrouter_client = OpenRouterClient(
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.OPENROUTER_MODEL,
        base_url=settings.OPENROUTER_BASE_URL,
        timeout=settings.OPENROUTER_TIMEOUT
    )

    # 4. Constrói prompt
    analysis_depth = options.get("analysis_depth", "standard")
    include_timestamps = options.get("include_timestamps", True)
    language = options.get("language", "pt-BR")
    extract_entities = options.get("extract_entities", False)
    detect_sentiment = options.get("detect_sentiment", False)

    prompt = openrouter_client.build_analysis_prompt(
        include_timestamps=include_timestamps,
        language=language,
        extract_entities=extract_entities,
        detect_sentiment=detect_sentiment,
        analysis_depth=analysis_depth
    )

    # 5. Chama OpenRouter
    logger.info("Calling OpenRouter API", job_id=job_id)
    openrouter_response = await openrouter_client.analyze_video(
        video_path=video_url,
        prompt=prompt,
        max_tokens=4000,
        temperature=0.7
    )

    # Extrai resposta
    markdown_analysis = openrouter_response["choices"][0]["message"]["content"]
    tokens_used = openrouter_response.get("usage", {}).get("total_tokens", 0)
    processing_time_ms = int((datetime.utcnow() - datetime.utcnow()).total_seconds() * 1000)

    # 6. Parse e estrutura resposta
    analysis_metadata = AnalysisMetadata(
        language_detected=language,
        topics=[],  # TODO: extrair de markdown
        sentiment=None  # TODO: extrair de markdown
    )

    analysis = Analysis(
        markdown=markdown_analysis,
        summary=_extract_summary(markdown_analysis),
        metadata=analysis_metadata
    )

    ai_provider = AIProviderInfo(
        provider="openrouter",
        model=settings.OPENROUTER_MODEL,
        tokens_used=tokens_used,
        processing_time_ms=processing_time_ms
    )

    result = AnalysisResult(
        video_metadata=video_metadata,
        analysis=analysis,
        ai_provider=ai_provider
    )

    end_time = datetime.utcnow()

    # 7. Formata resposta final
    response = VideoAnalysisResponse(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        created_at=start_time,
        completed_at=end_time,
        processing_time_seconds=(end_time - start_time).total_seconds(),
        result=result,
        links=Links(
            self=f"/api/v1/jobs/{job_id}",
            status=f"/api/v1/jobs/{job_id}",
            cancel=None
        )
    )

    await openrouter_client.close()

    return response.model_dump(mode='json')


def _extract_summary(markdown: str) -> str:
    """
    Extrai summary do markdown

    Args:
        markdown: Conteúdo markdown

    Returns:
        Summary em texto plano (primeiros 500 chars)
    """
    # Simples: tira markdown e pega primeiros parágrafos
    lines = [l.strip() for l in markdown.split("\n") if l.strip()]
    summary = " ".join(lines[:3])
    return summary[:500]


def _update_job_status(job_id: str, status: JobStatus) -> None:
    """
    Atualiza status do job no Redis

    Args:
        job_id: ID do job
        status: Novo status
    """
    try:
        redis_client.hset(
            f"job:{job_id}",
            "status",
            status.value
        )
        redis_client.expire(f"job:{job_id}", settings.JOB_RESULT_TTL)
    except Exception as e:
        logger.error("Failed to update job status", job_id=job_id, error=str(e))


def _store_result(job_id: str, result: dict) -> None:
    """
    Armazena resultado no Redis

    Args:
        job_id: ID do job
        result: Resultado da análise
    """
    try:
        redis_client.hset(
            f"job:{job_id}",
            "result",
            json.dumps(result)
        )
        redis_client.hset(
            f"job:{job_id}",
            "status",
            JobStatus.COMPLETED.value
        )
        redis_client.expire(f"job:{job_id}", settings.JOB_RESULT_TTL)
        logger.info("Result stored in Redis", job_id=job_id)
    except Exception as e:
        logger.error("Failed to store result", job_id=job_id, error=str(e))


def _store_error(job_id: str, error_message: str, error_code: str) -> None:
    """
    Armazena erro no Redis

    Args:
        job_id: ID do job
        error_message: Mensagem de erro
        error_code: Código do erro
    """
    try:
        redis_client.hset(
            f"job:{job_id}",
            mapping={
                "status": JobStatus.FAILED.value,
                "error": error_message,
                "error_code": error_code
            }
        )
        redis_client.expire(f"job:{job_id}", settings.JOB_RESULT_TTL)
        logger.info("Error stored in Redis", job_id=job_id, error_code=error_code)
    except Exception as e:
        logger.error("Failed to store error", job_id=job_id, error=str(e))


# Variável global para tracking do tempo de início
start_time = datetime.utcnow()
