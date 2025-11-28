"""
Rotas para análise de vídeos
"""
import uuid
from datetime import datetime
import json
import structlog
import redis
from fastapi import APIRouter, HTTPException, status

from app.models.requests import VideoAnalysisRequest
from app.models.responses import JobSubmittedResponse, VideoAnalysisResponse, JobStatus, Links, ErrorInfo, ErrorCode
from app.workers.tasks import analyze_video
from app.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["Video Analysis"])

# Cliente Redis
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)


@router.post(
    "",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submeter análise de vídeo",
    description="Enfileira um vídeo para análise assíncrona. Retorna job_id para consulta posterior."
)
async def submit_video_analysis(request: VideoAnalysisRequest) -> JobSubmittedResponse:
    """
    Submete um vídeo para análise.

    Retorna imediatamente com um job_id. Use este ID para consultar o status
    e resultado da análise.

    **Exemplo:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/jobs \\
      -H "Content-Type: application/json" \\
      -d '{
        "video_url": "file:///C:/videos/sample.mp4",
        "options": {
          "analysis_depth": "detailed"
        }
      }'
    ```
    """
    try:
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow()

        logger.info(
            "Video analysis submitted",
            job_id=job_id,
            video_url=request.video_url,
            options=request.options.model_dump() if request.options else None
        )

        # Enfileira task Celery
        task = analyze_video.apply_async(
            args=[job_id, request.model_dump()],
            task_id=job_id
        )

        logger.info("Task enqueued", job_id=job_id, celery_task_id=task.id)

        # Armazena info no Redis
        redis_client.hset(
            f"job:{job_id}",
            mapping={
                "status": JobStatus.PENDING.value,
                "created_at": created_at.isoformat()
            }
        )
        redis_client.expire(f"job:{job_id}", settings.JOB_RESULT_TTL)

        return JobSubmittedResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=created_at,
            estimated_time_seconds=180,  # Estimativa genérica
            links=Links(
                self=f"/api/v1/jobs/{job_id}",
                status=f"/api/v1/jobs/{job_id}",
                cancel=f"/api/v1/jobs/{job_id}/cancel"
            )
        )

    except Exception as e:
        logger.error("Error submitting job", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar requisição: {str(e)}"
        )


@router.get(
    "/{job_id}",
    response_model=VideoAnalysisResponse,
    summary="Obter status/resultado da análise",
    description="Retorna o status atual ou resultado completo da análise de vídeo."
)
async def get_analysis_result(job_id: str) -> VideoAnalysisResponse:
    """
    Consulta o status ou resultado de uma análise de vídeo.

    **Estados possíveis:**
    - `pending`: Job enfileirado, aguardando processamento
    - `processing`: Análise em andamento
    - `completed`: Análise concluída com sucesso
    - `failed`: Falha no processamento

    **Exemplo:**
    ```bash
    curl http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
    ```
    """
    try:
        logger.info("Getting analysis result", job_id=job_id)

        # Busca data no Redis
        job_data = redis_client.hgetall(f"job:{job_id}")

        if not job_data:
            logger.warning("Job not found", job_id=job_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} não encontrado"
            )

        # Extrai campos
        status_str = job_data.get("status", JobStatus.PENDING.value)
        status_enum = JobStatus(status_str)

        created_at_str = job_data.get("created_at")
        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.utcnow()

        # Constrói resposta
        response = VideoAnalysisResponse(
            job_id=job_id,
            status=status_enum,
            created_at=created_at,
            processing_time_seconds=None,
            links=Links(
                self=f"/api/v1/jobs/{job_id}",
                status=f"/api/v1/jobs/{job_id}",
                cancel=f"/api/v1/jobs/{job_id}/cancel" if status_enum == JobStatus.PENDING else None
            )
        )

        # Se tiver resultado, adiciona
        if "result" in job_data:
            try:
                result_data = json.loads(job_data["result"])
                # Aqui você teria que reconstruir os objetos Pydantic
                # Por simplicidade, deixamos como dict por agora
                response.result = result_data
                if "completed_at" in result_data:
                    response.completed_at = datetime.fromisoformat(result_data["completed_at"])
                if "processing_time_seconds" in result_data:
                    response.processing_time_seconds = result_data["processing_time_seconds"]
            except json.JSONDecodeError:
                logger.warning("Failed to parse result JSON", job_id=job_id)

        # Se tiver erro
        if "error" in job_data:
            response.error = ErrorInfo(
                code=ErrorCode(job_data.get("error_code", "INTERNAL_ERROR")),
                message=job_data["error"],
                details=job_data.get("error_details")
            )

        logger.info("Result retrieved", job_id=job_id, status=status_enum)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting result", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar resultado: {str(e)}"
        )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancelar ou deletar análise"
)
async def cancel_analysis(job_id: str) -> None:
    """
    Cancela job em andamento ou deleta resultado de job completo.

    **Exemplo:**
    ```bash
    curl -X DELETE http://localhost:8000/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
    ```
    """
    try:
        logger.info("Canceling/deleting job", job_id=job_id)

        # Revoga task Celery
        analyze_video.control.revoke(job_id, terminate=True)

        # Remove do Redis
        redis_client.delete(f"job:{job_id}")

        logger.info("Job canceled", job_id=job_id)

    except Exception as e:
        logger.error("Error canceling job", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao cancelar job: {str(e)}"
        )


@router.get(
    "",
    summary="Listar jobs (básico)",
    description="Retorna lista de jobs armazenados (implementação básica)"
)
async def list_jobs() -> dict:
    """
    Lista jobs recentes (implementação básica para teste).

    **Nota:** Em produção, isso teria paginação e filtros.
    """
    try:
        # Busca todas as chaves de jobs
        keys = redis_client.keys("job:*")
        jobs = []

        for key in keys[:10]:  # Limita a 10 para teste
            job_id = key.replace("job:", "")
            job_data = redis_client.hgetall(key)
            jobs.append({
                "job_id": job_id,
                "status": job_data.get("status"),
                "created_at": job_data.get("created_at")
            })

        return {
            "count": len(jobs),
            "jobs": jobs
        }

    except Exception as e:
        logger.error("Error listing jobs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar jobs: {str(e)}"
        )
