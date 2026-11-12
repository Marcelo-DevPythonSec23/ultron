"""Provedor NVIDIA NIM para o ULTRON 2.0.

Implementa o contrato `LLMProvider` usando a API NVIDIA com compatibilidade
OpenAI em `https://integrate.api.nvidia.com/v1`.

A chave de API é lida exclusivamente da variável de ambiente `NVIDIA_API_KEY`,
nunca gravada em código nem exposta em logs.

Componentes:
- `NVIDIAProvider`: implementação do provedor NVIDIA NIM
- `NVIDIA_PROVIDER_ID`: identificador constante "nvidia"
- `NVIDIA_DEFAULT_MODEL`: modelo padrão configurável via env
"""

from __future__ import annotations

import os
from typing import Any

from app.intelligence.providers.base import LLMException, LLMProvider
from app.models.message import (
    ChatMessage,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    MessageRole,
)

try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletion
except Exception:  # openai pode não estar instalado
    AsyncOpenAI = None  # type: ignore[assignment]
    ChatCompletion = None  # type: ignore[assignment]


PROVIDER_ID = "nvidia"
DEFAULT_MODEL = "nvidia/nemotron-3.5-flash"
API_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NVIDIAProvider(LLMProvider):
    """Adaptador do provedor NVIDIA NIM para o ULTRON 2.0.

    Usa a API compatível com OpenAI da NVIDIA NIM.
    A chave de API vem exclusivamente de `NVIDIA_API_KEY` (variável de
    ambiente), nunca é gravada em código nem exposta em logs.
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
        base_url: str = API_BASE_URL,
    ) -> None:
        self._api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        self._default_model = default_model
        self._base_url = base_url
        self._client: AsyncOpenAI | None = None

        if AsyncOpenAI is None:
            raise RuntimeError(
                "openai não está instalado. Instale com: pip install openai"
            )

        if self._api_key:
            self._client = AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
            )

    @property
    def provider_id(self) -> str:
        return PROVIDER_ID

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def available(self) -> bool:
        """Indica se o provedor está configurado com chave de API."""
        return self._client is not None

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Gera uma resposta completa usando o modelo NVIDIA NIM."""
        if not self._client:
            raise ProviderAuthenticationError(
                "NVIDIA_API_KEY não configurada. Defina a variável de ambiente "
                "NVIDIA_API_KEY para usar o provedor NVIDIA NIM.",
                provider=self.provider_id,
            )

        try:
            completion = await self._client.chat.completions.create(
                model=request.model or self._default_model,
                messages=[
                    {"role": m.role, "content": m.content}
                    for m in (request.messages or [])
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False,
            )
            assert isinstance(completion, ChatCompletion)

            content = completion.choices[0].message.content or ""
            usage = completion.usage

            return LLMResponse(
                content=content,
                provider=self.provider_id,
                model=request.model or self._default_model,
                usage=LLMUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                ),
            )
        except Exception as exc:  # noqa: BLE001 — erro de provedor externo
            self._raise_provider_error(exc)

    async def generate_stream(
        self, request: LLMRequest
    ):
        """Gera resposta em streaming usando o modelo NVIDIA NIM."""
        if not self._client:
            raise ProviderAuthenticationError(
                "NVIDIA_API_KEY não configurada.",
                provider=self.provider_id,
            )

        try:
            stream = await self._client.chat.completions.create(
                model=request.model or self._default_model,
                messages=[
                    {"role": m.role, "content": m.content}
                    for m in (request.messages or [])
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as exc:  # noqa: BLE001
            self._raise_provider_error(exc)

    async def health_check(self) -> bool:
        """Verifica se o provedor NVIDIA NIM está disponível."""
        if not self._client:
            return False
        try:
            await self._client.chat.completions.create(
                model=self._default_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )
            return True
        except Exception:  # noqa: BLE001
            return False

    def _raise_provider_error(self, exc: Exception) -> None:
        """Converte exceções do provedor para erros do contrato LLM."""
        msg = str(exc)

        # Erros de autenticação
        if "401" in msg or "authentication" in msg.lower() or "api key" in msg.lower():
            raise ProviderAuthenticationError(
                f"Falha de autenticação com NVIDIA NIM: {msg}",
                provider=self.provider_id,
            ) from exc

        # Erros de rate limit
        if "429" in msg or "rate limit" in msg.lower() or "quota" in msg.lower():
            raise ProviderRateLimitError(
                f"Limite de taxa excedido no NVIDIA NIM: {msg}",
                provider=self.provider_id,
            ) from exc

        # Erros de conexão/timeout
        if "timeout" in msg.lower() or "connection" in msg.lower():
            raise ProviderTimeoutError(
                f"Timeout na conexão com NVIDIA NIM: {msg}",
                provider=self.provider_id,
            ) from exc

        # Erro de requisição inválida
        if "400" in msg or "invalid request" in msg.lower():
            raise ProviderInvalidRequestError(
                f"Requisição inválida para NVIDIA NIM: {msg}",
                provider=self.provider_id,
            ) from exc

        # Erro de recurso não encontrado (modelo)
        if "404" in msg or "not found" in msg.lower():
            raise ProviderNotFoundError(
                f"Recurso não encontrado no NVIDIA NIM: {msg}",
                provider=self.provider_id,
            ) from exc

        # Erro de acesso negado
        if "403" in msg or "access denied" in msg.lower():
            raise ProviderAccessDeniedError(
                f"Acesso negado pelo NVIDIA NIM: {msg}",
                provider=self.provider_id,
            ) from exc

        # Erro de serviço indisponível
        if "503" in msg or "unavailable" in msg.lower():
            raise ProviderUnavailableError(
                f"Provedor NVIDIA NIM indisponível: {msg}",
                provider=self.provider_id,
            ) from exc

        # Erro genérico de resposta
        raise ProviderResponseError(
            f"Erro no provedor NVIDIA NIM: {msg}",
            provider=self.provider_id,
        ) from exc


__all__ = ["NVIDIAProvider", "PROVIDER_ID", "DEFAULT_MODEL", "API_BASE_URL"]
