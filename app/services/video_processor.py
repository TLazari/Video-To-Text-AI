"""
Serviço para processamento de vídeos
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

from app.core.exceptions import (
    VideoValidationError,
    VideoNotFoundError,
    UnsupportedFormatError,
    VideoTooLargeError,
    VideoProcessingError,
)
from app.config import settings

logger = structlog.get_logger(__name__)


class VideoProcessorService:
    """Serviço para processar vídeos"""

    @staticmethod
    async def validate_video(video_url: str) -> Dict[str, Any]:
        """
        Valida o vídeo via URL HTTP

        Args:
            video_url: URL HTTP do vídeo (http://... ou https://...)

        Returns:
            Dict com informações do vídeo

        Raises:
            VideoValidationError: Se vídeo for inválido
        """
        logger.info("Validating video", video_url=video_url)

        try:
            import httpx

            # Valida que é URL HTTP
            if not (video_url.startswith("http://") or video_url.startswith("https://")):
                raise VideoValidationError(
                    "URL deve ser HTTP ou HTTPS"
                )

            # Valida formato pelo nome da URL
            file_extension = video_url.split(".")[-1].split("?")[0].lower()
            if file_extension not in settings.SUPPORTED_FORMATS:
                raise UnsupportedFormatError(
                    f"Formato '{file_extension}' não suportado. "
                    f"Formatos aceitos: {', '.join(settings.SUPPORTED_FORMATS)}"
                )

            # Tenta fazer HEAD request para validar acesso
            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    response = await client.head(video_url)
                    response.raise_for_status()
                except httpx.HTTPError as e:
                    raise VideoNotFoundError(
                        f"Não foi possível acessar URL: {str(e)}"
                    )

                # Extrai tamanho do header
                content_length = response.headers.get("content-length")
                if content_length:
                    file_size_mb = int(content_length) / (1024 * 1024)

                    if file_size_mb > settings.MAX_VIDEO_SIZE_MB:
                        raise VideoTooLargeError(
                            f"Vídeo excede tamanho máximo de {settings.MAX_VIDEO_SIZE_MB}MB "
                            f"(tamanho atual: {file_size_mb:.2f}MB)"
                        )
                else:
                    file_size_mb = None

            logger.info(
                "Video validated",
                format=file_extension,
                size_mb=file_size_mb
            )

            return {
                "url": video_url,
                "format": file_extension,
                "size_mb": file_size_mb or 0
            }

        except (VideoValidationError, VideoNotFoundError, UnsupportedFormatError, VideoTooLargeError):
            raise
        except Exception as e:
            logger.error("Video validation error", error=str(e))
            raise VideoProcessingError(f"Erro ao validar vídeo: {str(e)}")

    @staticmethod
    async def extract_metadata(video_url: str) -> Dict[str, Any]:
        """
        Extrai metadados básicos do vídeo pela URL

        Nota: Para URLs HTTP, extrair metadados completos (duração, fps, etc)
        requer download do arquivo. Por enquanto, retornamos metadados básicos
        que será complementado pela análise do OpenRouter.

        Args:
            video_url: URL HTTP do vídeo

        Returns:
            Dict com metadados básicos do vídeo
        """
        logger.info("Extracting video metadata", video_url=video_url)

        try:
            import httpx

            # Faz HEAD request para extrair headers
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.head(video_url)
                response.raise_for_status()

                # Extrai informações dos headers
                content_length = response.headers.get("content-length")
                content_type = response.headers.get("content-type", "")

                file_size_mb = 0
                if content_length:
                    file_size_mb = int(content_length) / (1024 * 1024)

                # Extrai extensão da URL
                file_extension = video_url.split(".")[-1].split("?")[0].lower()

                logger.info(
                    "Metadata extracted",
                    size_mb=file_size_mb,
                    format=file_extension
                )

                return {
                    "duration_seconds": 0,  # Será extraído após processar
                    "resolution": "unknown",  # Será extraído após processar
                    "fps": 0,  # Será extraído após processar
                    "codec": "unknown",
                    "frame_count": 0,
                    "file_size_mb": file_size_mb,
                    "content_type": content_type,
                }

        except Exception as e:
            logger.error("Metadata extraction error", error=str(e))
            # Não lança erro, apenas retorna dados básicos
            return {
                "duration_seconds": 0,
                "resolution": "unknown",
                "fps": 0,
                "codec": "unknown",
                "frame_count": 0,
                "file_size_mb": 0,
                "content_type": "",
            }
