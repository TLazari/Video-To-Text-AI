"""
Core module
"""
from app.core.exceptions import (
    VideoAPIException,
    VideoValidationError,
    VideoNotFoundError,
    UnsupportedFormatError,
    VideoTooLargeError,
    RateLimitError,
    VideoProcessingError,
    OpenRouterAPIError,
    ProcessingTimeoutError,
    InternalProcessingError,
)

__all__ = [
    "VideoAPIException",
    "VideoValidationError",
    "VideoNotFoundError",
    "UnsupportedFormatError",
    "VideoTooLargeError",
    "RateLimitError",
    "VideoProcessingError",
    "OpenRouterAPIError",
    "ProcessingTimeoutError",
    "InternalProcessingError",
]
