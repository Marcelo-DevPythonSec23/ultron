"""Gerenciador de fallback entre provedores.

Recebe uma lista ORDENADA de adaptadores (já filtrada pela política) e tenta
cada um até obter uma resposta. Cada provedor é isolado: falha/timeout de um
não impede o próximo, as métricas são registradas por provedor e a ÚLTIMA
exceção é propagada sem embrulho (contrato de erro do lain preservado).

Fallback entre provedores é opt-in (`RouterConfig.fallback_enabled`): trocar
silenciosamente de provedor pode mudar custo, qualidade e privacidade, então
a decisão fica explícita na configuração operacional.
"""

from __future__ import annotations

import time

from app.models.message import LLMRequest, LLMResponse

from .adapters import ProviderAdapter
from .metrics import MetricsRegistry
from .retry import RetryManager


class FallbackManager:
    """Executa candidatos em ordem, com retry por candidato."""

    def __init__(
        self,
        *,
        metrics: MetricsRegistry,
        retry: RetryManager,
        timeout_seconds: float,
        cooldown_seconds: float,
    ) -> None:
        self._metrics = metrics
        self._retry = retry
        self._timeout = float(timeout_seconds)
        self._cooldown = float(cooldown_seconds)

    async def generate(
        self, adapters: list[ProviderAdapter], request: LLMRequest
    ) -> LLMResponse:
        if not adapters:
            raise RuntimeError("nenhum provedor candidato disponível")

        last_error: BaseException | None = None
        for adapter in adapters:
            provider_id = adapter.provider_id
            self._metrics.record_call(provider_id)
            started = time.monotonic()
            try:
                response = await self._retry.run(
                    lambda adapter=adapter: adapter.call(
                        request, timeout=self._timeout
                    ),
                    provider_id=provider_id,
                )
            except Exception as error:  # noqa: BLE001 — failover classifica
                last_error = error
                self._metrics.record_failure(
                    provider_id, error, cooldown_seconds=self._cooldown
                )
                continue
            self._metrics.record_success(
                provider_id, time.monotonic() - started
            )
            return response

        assert last_error is not None  # pragma: no cover — lista não vazia
        raise last_error
