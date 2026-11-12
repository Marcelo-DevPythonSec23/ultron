"""Adaptador de provedor: capacidades + execução com timeout.

O `ProviderAdapter` é a única camada que fala com o provedor real. Ele:

* fixa o modelo do candidato na requisição (sem mutar o objeto original);
* aplica timeout com `asyncio.wait_for` e converte estouro para
  `ProviderTimeoutError` do contrato do lain;
* abre streams com timeout até o PRIMEIRO chunk, para que o fallback só
  aconteça antes de qualquer texto já ter sido entregue ao usuário.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from app.intelligence.providers.base import LLMProvider, ProviderTimeoutError
from app.models.message import LLMRequest, LLMResponse

from .capabilities import ModelCapabilities


class ProviderAdapter:
    """Par provedor+modelo pronto para execução."""

    def __init__(self, provider: LLMProvider, capabilities: ModelCapabilities) -> None:
        self.provider = provider
        self.capabilities = capabilities

    @property
    def provider_id(self) -> str:
        return self.capabilities.provider_id

    @property
    def model(self) -> str:
        return self.capabilities.model

    def request_for(self, request: LLMRequest) -> LLMRequest:
        """Cópia da requisição com o modelo do candidato."""
        return request.model_copy(update={"model": self.model})

    async def call(self, request: LLMRequest, *, timeout: float) -> LLMResponse:
        try:
            return await asyncio.wait_for(
                self.provider.generate_response(self.request_for(request)),
                timeout=timeout,
            )
        except TimeoutError as error:
            raise ProviderTimeoutError(
                f"timeout de {timeout:g}s no provedor '{self.provider_id}'",
                provider=self.provider_id,
            ) from error

    async def open_stream(
        self, request: LLMRequest, *, timeout: float
    ) -> tuple[AsyncGenerator[str, None], str]:
        """Abre o stream e obtém o primeiro chunk sob timeout.

        Retorna `(generator, primeiro_chunk)`. Um stream vazio é aceito como
        sucesso com chunk vazio. Falhas antes do primeiro chunk fecham o
        gerador e propagam a exceção (o roteador pode tentar outro candidato).
        """
        generator = self.provider.generate_stream(self.request_for(request))
        try:
            first = await asyncio.wait_for(generator.__anext__(), timeout=timeout)
        except StopAsyncIteration:
            await generator.aclose()
            return _empty_stream(), ""
        except TimeoutError as error:
            await generator.aclose()
            raise ProviderTimeoutError(
                f"timeout de {timeout:g}s no provedor '{self.provider_id}'",
                provider=self.provider_id,
            ) from error
        except Exception:
            await generator.aclose()
            raise
        return generator, first

    async def health_check(self, *, timeout: float) -> bool:
        try:
            return bool(
                await asyncio.wait_for(self.provider.health_check(), timeout=timeout)
            )
        except Exception:  # noqa: BLE001 — health é diagnóstico, nunca derruba
            return False


async def _empty_stream() -> AsyncGenerator[str, None]:
    return
    yield ""  # pragma: no cover — marca a função como geradora
