"""
Exceções customizadas para a API
"""
from typing import Optional
from app.models.responses import ErrorCode


class VideoAPIException(Exception):
    """Exceção base para a API"""
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
    http_status: int = 500

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)


# Erros de Cliente (4xx)

class VideoValidationError(VideoAPIException):
    """URL inválida, formato não suportado, vídeo muito grande"""
    error_code = ErrorCode.INVALID_VIDEO_URL
    http_status = 400


class VideoNotFoundError(VideoAPIException):
    """Vídeo não existe no caminho especificado"""
    error_code = ErrorCode.VIDEO_NOT_FOUND
    http_status = 404


class UnsupportedFormatError(VideoAPIException):
    """Formato de vídeo não suportado"""
    error_code = ErrorCode.UNSUPPORTED_FORMAT
    http_status = 400


class VideoTooLargeError(VideoAPIException):
    """Vídeo excede tamanho máximo"""
    error_code = ErrorCode.VIDEO_TOO_LARGE
    http_status = 413


class RateLimitError(VideoAPIException):
    """Cliente excedeu limite de requisições"""
    error_code = ErrorCode.RATE_LIMIT_EXCEEDED
    http_status = 429

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


# Erros de Servidor (5xx)

class VideoProcessingError(VideoAPIException):
    """Erro ao processar vídeo"""
    error_code = ErrorCode.VIDEO_PROCESSING_ERROR
    http_status = 500


class OpenRouterAPIError(VideoAPIException):
    """Erro na comunicação com OpenRouter"""
    error_code = ErrorCode.OPENROUTER_API_ERROR
    http_status = 502


class ProcessingTimeoutError(VideoAPIException):
    """Processamento excedeu timeout"""
    error_code = ErrorCode.TIMEOUT_ERROR
    http_status = 504


class InternalProcessingError(VideoAPIException):
    """Erro interno não esperado"""
    error_code = ErrorCode.INTERNAL_ERROR
    http_status = 500
