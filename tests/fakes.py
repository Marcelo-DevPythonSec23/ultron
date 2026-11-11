"""Fakes de teste: provedor LLM scriptável (não é mock de unidade — é um
provedor REAL do contrato LLMProvider que devolve respostas ensaiadas em
sequência, para exercitar o loop de ferramentas ponta a ponta sem rede).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.intelligence.providers.base import LLMProvider
from app.models.message import LLMRequest, LLMResponse, LLMUsage, MessageRole


class ScriptedProvider(LLMProvider):
    """Provedor que devolve `responses` em ordem, uma por chamada.

    Registra cada LLMRequest recebido em `calls` para que os testes possam
    inspecionar o que o orquestrador/proxy realmente enviou ao modelo
    (histórico, marcadores [TOOL_RESULT], prompt de sistema...).
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[LLMRequest] = []

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "scripted-model"

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        content = self._responses.pop(0) if self._responses else "scripted-exhausted"
        return LLMResponse(
            content=content,
            role=MessageRole.ASSISTANT,
            provider=self.provider_id,
            model=request.model or self.default_model,
            usage=LLMUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            raw_metadata={"scripted": True},
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        response = await self.generate_response(request)
        yield response.content

    async def health_check(self) -> bool:
        return True


class StubProvider(LLMProvider):
    """Provedor configurável com identidade própria (Fase 3).

    Diferente do `ScriptedProvider` (sempre `provider_id="mock"`), este stub
    permite simular DOIS provedores distintos para exercitar seleção,
    fallback, retry, timeout e streaming sem rede.
    """

    def __init__(
        self,
        provider_id: str,
        *,
        model: str = "stub-model",
        responses: list[str] | None = None,
        error: BaseException | None = None,
        fail_times: int = 0,
        delay_seconds: float = 0.0,
        stream_chunks: list[str] | None = None,
        stream_error_after: int | None = None,
    ) -> None:
        self._provider_id = provider_id
        self._model = model
        self._responses = list(responses or [])
        self._error = error
        self._fail_remaining = int(fail_times)
        self._delay = max(0.0, float(delay_seconds))
        self._stream_chunks = list(stream_chunks) if stream_chunks is not None else None
        self._stream_error_after = stream_error_after
        self.calls: list[LLMRequest] = []
        self.attempts = 0

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def default_model(self) -> str:
        return self._model

    async def _next_content(self, request: LLMRequest) -> str:
        self.calls.append(request)
        self.attempts += 1
        if self._delay:
            import asyncio

            await asyncio.sleep(self._delay)
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise self._error or RuntimeError(f"{self._provider_id} indisponível")
        return (
            self._responses.pop(0)
            if self._responses
            else f"{self._provider_id}-ok"
        )

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        content = await self._next_content(request)
        return LLMResponse(
            content=content,
            role=MessageRole.ASSISTANT,
            provider=self.provider_id,
            model=request.model or self.default_model,
            usage=LLMUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            raw_metadata={"stub": True},
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        content = await self._next_content(request)
        chunks = self._stream_chunks if self._stream_chunks is not None else [content]
        for index, chunk in enumerate(chunks):
            if (
                self._stream_error_after is not None
                and index >= self._stream_error_after
            ):
                raise RuntimeError(f"{self._provider_id} stream interrompido")
            yield chunk

    async def health_check(self) -> bool:
        return True
