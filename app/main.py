"""
Aplicação FastAPI principal
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from contextlib import asynccontextmanager

from app.config import settings
from app.core.exceptions import VideoAPIException
from app.api.v1.routes import videos, files
from app.models.responses import ErrorInfo

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia ciclo de vida da aplicação
    """
    logger.info(
        "Application starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG
    )

    try:
        # Tenta conectar ao Redis para validar setup
        import redis
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
        )
        redis_client.ping()
        logger.info("Redis connection successful", redis_host=settings.REDIS_HOST)
    except Exception as e:
        logger.warning(
            "Redis connection failed",
            redis_host=settings.REDIS_HOST,
            error=str(e)
        )

    yield

    logger.info("Application shutdown")


# Cria app FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para análise de vídeos com OpenRouter",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Handler de exceções customizadas
@app.exception_handler(VideoAPIException)
async def video_api_exception_handler(request: Request, exc: VideoAPIException):
    """Handle custom VideoAPIException"""
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error": {
                "code": exc.error_code.value,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Verifica saúde da aplicação
    """
    try:
        import redis
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
        )
        redis_client.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "redis": redis_status
    }


# Root endpoint
@app.get("/", tags=["Info"])
async def root():
    """
    Informações sobre a API
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/health",
            "api": settings.API_PREFIX
        }
    }


# Registra rotas
app.include_router(videos.router, prefix=settings.API_PREFIX)
app.include_router(files.router, prefix=settings.API_PREFIX)

logger.info("FastAPI app configured", api_prefix=settings.API_PREFIX)
