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
