"""
Rotas para servir arquivos (vídeos, etc)
"""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/videos", tags=["Files"])

# Diretório de vídeos
VIDEOS_DIR = Path("/videos")


@router.get("/{filename}", summary="Download/Stream de vídeo")
async def serve_video(filename: str):
    """
    Serve um vídeo do diretório /videos.

    **Uso:**
    - Stream: `http://localhost:8000/api/v1/videos/sample.mp4`
    - Para análise: use a URL acima em uma requisição POST para /jobs

    **Exemplo:**
    ```bash
    # Fazer download
    curl http://localhost:8000/api/v1/videos/sample.mp4 -o sample.mp4

    # Usar em análise
    curl -X POST http://localhost:8000/api/v1/jobs \\
      -H "Content-Type: application/json" \\
      -d '{
        "video_url": "http://localhost:8000/api/v1/videos/sample.mp4"
      }'
    ```
    """
    try:
        logger.info("Serving video", filename=filename)

        # Sanitiza filename para evitar path traversal
        safe_filename = os.path.basename(filename)

        # Constrói path completo
        file_path = VIDEOS_DIR / safe_filename

        # Valida que arquivo existe
        if not file_path.exists():
            logger.warning("Video not found", filename=filename, path=str(file_path))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vídeo '{filename}' não encontrado"
            )

        # Valida que é arquivo, não diretório
        if not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Caminho deve ser um arquivo"
            )

        logger.info("Video found", path=str(file_path), size_bytes=file_path.stat().st_size)

        # Retorna arquivo com streaming
        return FileResponse(
            file_path,
            media_type="video/mp4",
            filename=safe_filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error serving video", filename=filename, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao servir vídeo: {str(e)}"
        )


@router.get("", summary="Listar vídeos disponíveis")
async def list_videos():
    """
    Lista todos os vídeos disponíveis no diretório `/videos`.

    **Exemplo:**
    ```bash
    curl http://localhost:8000/api/v1/videos
    ```

    **Resposta:**
    ```json
    {
      "count": 2,
      "videos": [
        {
          "name": "sample.mp4",
          "size_mb": 45.2,
          "url": "http://localhost:8000/api/v1/videos/sample.mp4"
        }
      ]
    }
    ```
    """
    try:
        # Cria diretório se não existir
        os.makedirs(VIDEOS_DIR, exist_ok=True)

        # Lista arquivos de vídeo
        video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
        videos = []

        for file in VIDEOS_DIR.iterdir():
            if file.is_file() and file.suffix.lower() in video_extensions:
                size_bytes = file.stat().st_size
                size_mb = size_bytes / (1024 * 1024)

                videos.append({
                    "name": file.name,
                    "size_mb": round(size_mb, 2),
                    "size_bytes": size_bytes,
                    "url": f"http://localhost:8000/api/v1/videos/{file.name}"
                })

        logger.info("Videos listed", count=len(videos))

        return {
            "count": len(videos),
            "videos": sorted(videos, key=lambda x: x["name"])
        }

    except Exception as e:
        logger.error("Error listing videos", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar vídeos: {str(e)}"
        )
