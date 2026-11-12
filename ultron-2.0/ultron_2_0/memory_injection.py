"""Injeção de contexto de memória no turno (MEMORY.md §10).

A memória NÃO toma decisões: ela apenas fornece um bloco de fatos ao modelo,
que continua sendo chamado pelo orquestrador do lain. O wrapper fica FORA do
`ToolCallingProvider` (ordem em `UltronCoreRuntime._wrap`), então:

* a recuperação acontece uma vez por turno do usuário, a partir da última
  mensagem do usuário — não a cada rodada interna de ferramenta;
* o bloco entra no `system_instruction` e o `ToolCallingProvider` acrescenta o
  protocolo de ferramentas DEPOIS, sem apagar o contexto;
* nenhum histórico paralelo é criado: o histórico continua no SQLite do núcleo.

O bloco recuperado é marcado como DADO não confiável pelo `MemoryEngine`
(`get_context`), portanto uma memória vinda de página/ferramenta não se
converte em instrução do sistema só por estar armazenada.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Iterable
from typing import Any

from app.intelligence.providers.base import LLMProvider
from app.models.message import LLMRequest, LLMResponse, MessageRole

from .memory_engine import MemoryEngine

logger = logging.getLogger("ultron2.memory.injection")

_TOOL_RESULT_PREFIX = "[TOOL_RESULT"


def _last_user_query(request: LLMRequest) -> str:
    """Última mensagem real do usuário (ignora resultados de ferramenta)."""
    for message in reversed(request.messages or []):
        if getattr(message, "role", None) != MessageRole.USER:
            continue
        content = (message.content or "").strip()
        if content.startswith(_TOOL_RESULT_PREFIX):
            continue
        return content[:500]
    return ""


class MemoryInjectionProvider(LLMProvider):
    """Proxy de provedor que injeta memória relevante no prompt do turno."""

    def __init__(
        self,
        inner: LLMProvider,
        engine: MemoryEngine,
        *,
        scopes: Iterable[str] | None = None,
        budget_chars: int = 1200,
        limit: int = 12,
    ) -> None:
        self._inner = inner
        self._engine = engine
        self._scopes = tuple(scopes) if scopes is not None else engine.read_scopes
        self._budget_chars = max(0, int(budget_chars))
        self._limit = max(1, int(limit))

    # -- identidade delegada --------------------------------------------------
    @property
    def provider_id(self) -> str:
        return self._inner.provider_id

    @property
    def default_model(self) -> str:
        return self._inner.default_model

    async def health_check(self) -> bool:
        return await self._inner.health_check()

    # -- contexto -------------------------------------------------------------
    async def _augment(self, request: LLMRequest) -> LLMRequest:
        query = _last_user_query(request)
        try:
            block = await asyncio.to_thread(
                self._engine.get_context,
                query,
                scopes=self._scopes,
                budget_chars=self._budget_chars,
                limit=self._limit,
            )
        except Exception:
            # Memória indisponível não pode derrubar a conversa: segue sem ela.
            logger.exception("falha ao recuperar memória; turno segue sem injeção")
            return request
        if not block:
            return request
        system = request.system_instruction or ""
        augmented = f"{system}\n\n{block}" if system else block
        return request.model_copy(update={"system_instruction": augmented})

    # -- contrato LLMProvider -------------------------------------------------
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        return await self._inner.generate_response(await self._augment(request))

    async def generate_stream(
        self, request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        augmented = await self._augment(request)
        async for chunk in self._inner.generate_stream(augmented):
            yield chunk

    async def generate_response_streaming(
        self, request: LLMRequest, on_chunk
    ) -> LLMResponse:
        """Delega o streaming com callback quando o interno o suporta."""
        augmented = await self._augment(request)
        streaming = getattr(self._inner, "generate_response_streaming", None)
        if streaming is None:
            response = await self._inner.generate_response(augmented)
            on_chunk(response.content or "")
            return response
        return await streaming(augmented, on_chunk)

    # -- diagnóstico ----------------------------------------------------------
    @property
    def engine(self) -> MemoryEngine:
        return self._engine

    @property
    def scopes(self) -> tuple[str, ...]:
        return self._scopes

    @property
    def budget_chars(self) -> int:
        return self._budget_chars

    def __getattr__(self, name: str) -> Any:  # delega atributos não mapeados
        return getattr(self._inner, name)
