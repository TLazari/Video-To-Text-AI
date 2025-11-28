"""
Cliente para integração com OpenRouter API
"""
import httpx
import base64
from typing import Dict, Any, Optional, List
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import structlog
from datetime import datetime

from app.core.circuit_breaker import CircuitBreaker
from app.core.exceptions import (
    OpenRouterAPIError,
    RateLimitError,
    ProcessingTimeoutError
)


logger = structlog.get_logger(__name__)


class OpenRouterClient:
    """
    Cliente para comunicação com OpenRouter API

    Features:
    - Circuit breaker para resiliência
    - Retry com backoff exponencial
    - Rate limiting handling
    - Timeout configurável
    - Logging estruturado
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openai/gpt-4-vision-preview",
        timeout: int = 120,
        max_retries: int = 3,
        app_name: str = "Video Analysis API",
        app_url: str = "https://your-app.com"
    ):
        """
        Args:
            api_key: Chave da API OpenRouter
            base_url: URL base da API
            model: Modelo a ser utilizado
            timeout: Timeout em segundos
            max_retries: Máximo de tentativas
            app_name: Nome da aplicação (para headers)
            app_url: URL da aplicação (para headers)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.app_name = app_name
        self.app_url = app_url

        # Client HTTP assíncrono
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": app_url,
                "X-Title": app_name,
                "Content-Type": "application/json"
            }
        )

        # Circuit breaker para proteção
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=OpenRouterAPIError
        )

        logger.info(
            "openrouter_client_initialized",
            model=model,
            timeout=timeout,
            max_retries=max_retries
        )

    async def _get_video_as_base64(self, video_url: str) -> str:
        """
        Converte vídeo (URL ou arquivo) para data URL em Base64

        Args:
            video_url: URL HTTP do vídeo ou caminho do arquivo

        Returns:
            Data URL no formato: data:video/mp4;base64,<dados>
        """
        logger.info("Converting video to base64", video_url=video_url)

        # Se for URL HTTP/HTTPS, faz download
        if video_url.startswith(("http://", "https://")):
            try:
                # Resolve URL para dentro de container Docker
                resolved_url = video_url
                if "localhost:8000" in video_url:
                    resolved_url = video_url.replace("localhost:8000", "host.docker.internal:8000")

                async with httpx.AsyncClient(timeout=300) as client:
                    response = await client.get(resolved_url)
                    response.raise_for_status()
                    video_data = response.content
                    logger.info("Video downloaded from URL", size_bytes=len(video_data))
            except Exception as e:
                logger.error("Failed to download video", error=str(e))
                raise OpenRouterAPIError(f"Failed to download video: {str(e)}")
        else:
            # Se for arquivo local, lê do disco
            try:
                with open(video_url, "rb") as f:
                    video_data = f.read()
                logger.info("Video read from disk", size_bytes=len(video_data))
            except Exception as e:
                logger.error("Failed to read video file", error=str(e))
                raise OpenRouterAPIError(f"Failed to read video file: {str(e)}")

        # Codifica em Base64
        base64_data = base64.b64encode(video_data).decode('utf-8')

        # Retorna como data URL (mp4 é padrão)
        data_url = f"data:video/mp4;base64,{base64_data}"
        logger.info("Video converted to base64", data_url_size=len(data_url))

        return data_url

    async def close(self):
        """Fecha conexões do cliente"""
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OpenRouterAPIError, httpx.TimeoutException)),
        reraise=True
    )
    async def _make_request(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Faz requisição à API com retry

        Args:
            endpoint: Endpoint da API (ex: /chat/completions)
            payload: Payload JSON

        Returns:
            Resposta JSON da API

        Raises:
            OpenRouterAPIError: Erro na comunicação
            RateLimitError: Rate limit excedido
            ProcessingTimeoutError: Timeout na requisição
        """
        url = f"{self.base_url}{endpoint}"

        logger.info(
            "openrouter_request_started",
            url=url,
            model=payload.get("model")
        )

        start_time = datetime.now()

        try:
            response = await self.client.post(url, json=payload)

            # Rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(
                    "openrouter_rate_limited",
                    retry_after=retry_after
                )
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after}s",
                    retry_after=retry_after
                )

            # Outros erros HTTP
            if response.status_code >= 400:
                error_detail = response.json() if response.text else {}
                logger.error(
                    "openrouter_http_error",
                    status_code=response.status_code,
                    error=error_detail
                )
                raise OpenRouterAPIError(
                    f"OpenRouter API error: {response.status_code} - {error_detail}"
                )

            result = response.json()

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(
                "openrouter_request_completed",
                processing_time_ms=processing_time,
                tokens_used=result.get("usage", {}).get("total_tokens", 0)
            )

            return result

        except httpx.TimeoutException as e:
            logger.error(
                "openrouter_timeout",
                timeout=self.timeout
            )
            raise ProcessingTimeoutError(
                f"Request timed out after {self.timeout}s"
            ) from e

        except httpx.RequestError as e:
            logger.error(
                "openrouter_request_error",
                error=str(e)
            )
            raise OpenRouterAPIError(
                f"Request failed: {str(e)}"
            ) from e

    async def analyze_video(
        self,
        video_path: str,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analisa vídeo usando modelo de visão (com Base64 embedding)

        Args:
            video_path: URL HTTP do vídeo ou caminho do arquivo local
            prompt: Prompt de análise
            max_tokens: Máximo de tokens na resposta
            temperature: Temperatura do modelo (0-1)

        Returns:
            Resposta da API com análise

        Raises:
            OpenRouterAPIError: Erro na API ou ao processar vídeo
            CircuitBreakerError: Circuit breaker aberto
        """

        @self.circuit_breaker
        async def _protected_call():
            # Converte vídeo para Base64
            video_data_url = await self._get_video_as_base64(video_path)

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Você é um especialista em análise de vídeos. "
                            "Forneça análises detalhadas, bem estruturadas em formato Markdown. "
                            "Seja objetivo, preciso e organize o conteúdo de forma clara."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "video_url",
                                "video_url": {
                                    "url": video_data_url
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            return await self._make_request("/chat/completions", payload)

        return await _protected_call()

    def build_analysis_prompt(
        self,
        include_timestamps: bool = True,
        language: str = "pt-BR",
        extract_entities: bool = False,
        detect_sentiment: bool = False,
        analysis_depth: str = "standard"
    ) -> str:
        """
        Constrói prompt de análise baseado nas opções

        Args:
            include_timestamps: Incluir timestamps
            language: Idioma da análise
            extract_entities: Extrair entidades
            detect_sentiment: Detectar sentimento
            analysis_depth: Profundidade (quick, standard, detailed)

        Returns:
            Prompt formatado
        """

        depth_instructions = {
            "quick": "Forneça uma análise concisa e objetiva.",
            "standard": "Forneça uma análise balanceada com bom nível de detalhes.",
            "detailed": "Forneça uma análise muito detalhada e aprofundada."
        }

        prompt_parts = [
            f"Analise este vídeo em {language}.",
            depth_instructions.get(analysis_depth, depth_instructions["standard"]),
            "",
            "Forneça a análise em formato Markdown bem estruturado, incluindo:",
            "- # Título principal da análise",
            "- ## Resumo Executivo (2-3 parágrafos)",
            "- ## Descrição Detalhada do Conteúdo",
            "- ## Elementos Visuais e Técnicos"
        ]

        if include_timestamps:
            prompt_parts.append("- ## Momentos-Chave (com timestamps no formato MM:SS)")

        if extract_entities:
            prompt_parts.append(
                "- ## Entidades Identificadas (pessoas, objetos, locais, marcas)"
            )

        if detect_sentiment:
            prompt_parts.append("- ## Análise de Sentimento/Tom")

        prompt_parts.extend([
            "- ## Conclusão",
            "",
            "Seja específico, objetivo e organize o conteúdo de forma hierárquica clara."
        ])

        return "\n".join(prompt_parts)

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Retorna status do circuit breaker"""
        return self.circuit_breaker.get_state()
