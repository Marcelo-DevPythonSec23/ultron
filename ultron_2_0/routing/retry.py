"""Política de retry com backoff exponencial e classificação de erros.

Regras (Fase 3, verificadas em `tests/test_routing.py`):

* erros transitórios — rate limit, indisponibilidade, timeout, conexão e
  resposta inválida — são tentados de novo até `max_attempts`, com backoff
  exponencial limitado por `max_backoff_seconds`;
* erros definitivos — autenticação, acesso negado, requisição inválida e
  recurso inexistente — NÃO são repetidos: insistir não resolve e pode
  consumir cota;
* exceções desconhecidas são tratadas como transitórias (uma tentativa extra),
  porque falhas de transporte nem sempre chegam tipadas.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.intelligence.providers.base import (
    LLMException,
    ProviderAccessDeniedError,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderInvalidRequestError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

from .metrics import MetricsRegistry

# Definitivos: repetir não ajuda.
NON_RETRYABLE: tuple[type[BaseException], ...] = (
    ProviderAuthenticationError,
    ProviderAccessDeniedError,
    ProviderInvalidRequestError,
    ProviderNotFoundError,
)

# Transitórios explícitos (documentação do porquê).
RETRYABLE: tuple[type[BaseException], ...] = (
    ProviderRateLimitError,
    ProviderUnavailableError,
    ProviderTimeoutError,
    ProviderConnectionError,
    ProviderResponseError,
)


@dataclass(frozen=True)
class RetryPolicy:
    """Parâmetros imutáveis de retry."""

    max_attempts: int = 2
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 4.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts deve ser >= 1")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("delays não podem ser negativos")

    def delay_for(self, attempt_index: int) -> float:
        """Backoff exponencial determinístico após a tentativa `attempt_index`."""
        if attempt_index < 0:
            raise ValueError("attempt_index deve ser >= 0")
        delay = self.base_delay_seconds * (2 ** attempt_index)
        return min(self.max_delay_seconds, delay)

    def should_retry(self, error: BaseException) -> bool:
        if isinstance(error, NON_RETRYABLE):
            return False
        if isinstance(error, LLMException):
            return True
        return True


class RetryManager:
    """Executa uma operação com retry e registra retries nas métricas."""

    def __init__(
        self,
        policy: RetryPolicy,
        *,
        metrics: MetricsRegistry | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self.policy = policy
        self._metrics = metrics
        self._sleep = sleep or asyncio.sleep

    async def run(
        self,
        operation: Callable[[], Awaitable[object]],
        *,
        provider_id: str,
    ):
        """Executa `operation()` até obter sucesso ou esgotar as tentativas.

        A última exceção é propagada SEM embrulho — o contrato de erro do
        lain (e os testes existentes) continua válido.
        """
        last_error: BaseException | None = None
        for attempt in range(self.policy.max_attempts):
            try:
                return await operation()
            except Exception as error:  # noqa: BLE001 — classificado abaixo
                last_error = error
                exhausted = attempt + 1 >= self.policy.max_attempts
                if exhausted or not self.policy.should_retry(error):
                    raise
                if self._metrics is not None:
                    self._metrics.record_retry(provider_id)
                await self._sleep(self.policy.delay_for(attempt))
        assert last_error is not None  # pragma: no cover — loop sempre retorna/levanta
        raise last_error
