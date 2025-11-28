"""
Circuit Breaker pattern para proteção de integrações externas
"""
import time
from typing import Callable, Any, Optional
from enum import Enum
import asyncio
from functools import wraps


class CircuitState(str, Enum):
    """Estados do Circuit Breaker"""
    CLOSED = "closed"      # Funcionamento normal
    OPEN = "open"          # Circuito aberto, rejeitando requisições
    HALF_OPEN = "half_open"  # Testando se serviço recuperou


class CircuitBreakerError(Exception):
    """Erro lançado quando circuito está aberto"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker para proteção de chamadas externas

    Exemplo:
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=OpenRouterAPIError
        )

        @breaker
        async def call_openrouter():
            # Sua chamada aqui
            pass
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        half_open_max_calls: int = 1
    ):
        """
        Args:
            failure_threshold: Número de falhas antes de abrir circuito
            recovery_timeout: Tempo em segundos antes de tentar recuperar
            expected_exception: Tipo de exceção que conta como falha
            half_open_max_calls: Chamadas permitidas em half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0

    def _should_attempt_reset(self) -> bool:
        """Verifica se deve tentar recuperar o circuito"""
        if self.state != CircuitState.OPEN:
            return False

        if self.last_failure_time is None:
            return False

        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _on_success(self):
        """Chamado quando operação é bem-sucedida"""
        if self.state == CircuitState.HALF_OPEN:
            # Sucesso em half-open: fecha circuito
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.half_open_calls = 0
        elif self.state == CircuitState.CLOSED:
            # Reset contador de falhas em caso de sucesso
            self.failure_count = 0

    def _on_failure(self):
        """Chamado quando operação falha"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Falha em half-open: abre circuito novamente
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
        elif self.failure_count >= self.failure_threshold:
            # Threshold atingido: abre circuito
            self.state = CircuitState.OPEN

    def __call__(self, func: Callable) -> Callable:
        """Decorator para funções síncronas e assíncronas"""

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Verifica se deve tentar recuperar
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0

            # Circuito aberto: rejeita requisição
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN. Service unavailable. "
                    f"Retry after {self.recovery_timeout}s"
                )

            # Half-open: limita chamadas
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerError(
                        "Circuit breaker is HALF_OPEN. Max test calls reached."
                    )
                self.half_open_calls += 1

            # Tenta executar função
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Mesma lógica para funções síncronas
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0

            if self.state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN. Service unavailable. "
                    f"Retry after {self.recovery_timeout}s"
                )

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerError(
                        "Circuit breaker is HALF_OPEN. Max test calls reached."
                    )
                self.half_open_calls += 1

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise

        # Retorna wrapper apropriado baseado no tipo de função
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    def get_state(self) -> dict:
        """Retorna estado atual do circuit breaker"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "time_until_retry": (
                max(0, self.recovery_timeout - (time.time() - self.last_failure_time))
                if self.last_failure_time else 0
            )
        }
