"""Adaptador do provedor Google Gemini utilizando o SDK oficial google-genai."""

import logging
import re
from collections.abc import AsyncGenerator, Callable

from google import genai
from google.genai import errors, types

from app.intelligence.providers.base import (
    LLMException,
    LLMProvider,
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
from app.models.message import (
    ChatMessage,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    MessageRole,
)

logger = logging.getLogger("ultron.providers.gemini")
_RETRY_DELAY = re.compile(
    r"(?:retry(?:\s+after|Delay)?|retry in)[^0-9]{0,20}"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|milliseconds?|s|seconds?|m|minutes?|h|hours?)",
    re.IGNORECASE,
)


class GeminiProvider(LLMProvider):
    """Adaptador de integração com os modelos Google Gemini via google-genai SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gemini-3.5-flash",
    ) -> None:
        self._api_key = api_key
        self._default_model = default_model
        self._client: genai.Client | None = None

        if api_key:
            self._client = genai.Client(api_key=api_key)

    @property
    def provider_id(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return self._default_model

    def _ensure_client(self) -> genai.Client:
        """Garante que o cliente foi inicializado com uma chave de API válida."""
        if not self._client or not self._api_key:
            raise ProviderAuthenticationError(
                "Chave de API do Google Gemini (GEMINI_API_KEY) não configurada.",
                provider=self.provider_id,
            )
        return self._client

    def _convert_messages_to_contents(
        self, messages: list[ChatMessage]
    ) -> list[types.Content]:
        """Converte mensagens canônicas para o formato de Contents esperado pela API Gemini."""
        contents: list[types.Content] = []
        for msg in messages:
            # Pula mensagens de sistema pois são passadas via GenerateContentConfig
            if msg.role == MessageRole.SYSTEM:
                continue

            gemini_role = "user" if msg.role == MessageRole.USER else "model"
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=msg.content)],
                )
            )
        return contents

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Envia a requisição à API Gemini de forma assíncrona e normaliza a resposta."""
        client = self._ensure_client()
        target_model = request.model or self.default_model

        # Montar configuração da geração
        config = types.GenerateContentConfig(
            system_instruction=request.system_instruction,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )

        contents = self._convert_messages_to_contents(request.messages)
        if not contents:
            raise ProviderInvalidRequestError(
                "Nenhuma mensagem de usuário fornecida para a geração.",
                provider=self.provider_id,
            )

        max_retries = 2
        response = None
        for attempt in range(max_retries + 1):
            try:
                response = await client.aio.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=config,
                )
                break
            except errors.APIError as exc:
                if exc.code in (500, 502, 503, 504) and attempt < max_retries:
                    logger.warning(
                        "Spike transitório na API Gemini (código %s). Nova tentativa em %ds...",
                        exc.code,
                        (attempt + 1) * 2,
                    )
                    import asyncio
                    await asyncio.sleep((attempt + 1) * 2)
                    continue

                self._handle_api_error(exc)
            except Exception as exc:
                normalized = self._normalize_transport_error(exc)
                if isinstance(normalized, ProviderUnavailableError) and attempt < max_retries:
                    import asyncio
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                raise normalized from exc

        if response is None:
            raise ProviderResponseError(
                "O provedor Gemini não retornou uma resposta válida.",
                provider=self.provider_id,
            )

        # Extrair texto retornado
        try:
            content_text = response.text or ""
        except (AttributeError, TypeError, ValueError) as exc:
            raise ProviderResponseError(
                "O provedor retornou uma resposta inválida.",
                provider=self.provider_id,
                details=self._safe_error_details(exc),
            ) from exc

        # Extrair métricas de consumo de tokens
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        if response.usage_metadata:
            prompt_tokens = response.usage_metadata.prompt_token_count or 0
            completion_tokens = response.usage_metadata.candidates_token_count or 0
            total_tokens = response.usage_metadata.total_token_count or (prompt_tokens + completion_tokens)

        return LLMResponse(
            content=content_text,
            role=MessageRole.ASSISTANT,
            provider=self.provider_id,
            model=target_model,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            raw_metadata={"model_version": getattr(response, "model_version", None)},
        )

    async def generate_response_streaming(
        self,
        request: LLMRequest,
        on_chunk: Callable[[str], None],
    ) -> LLMResponse:
        """Transmite a resposta do Gemini e retorna métricas da geração completa."""
        target_model = request.model or self.default_model
        chunks: list[str] = []
        usage_metadata = None
        async for response_chunk in self._generate_content_stream(request):
            text = response_chunk.text or ""
            if text:
                chunks.append(text)
                on_chunk(text)
            if response_chunk.usage_metadata:
                usage_metadata = response_chunk.usage_metadata

        prompt_tokens = usage_metadata.prompt_token_count or 0 if usage_metadata else 0
        completion_tokens = (
            usage_metadata.candidates_token_count or 0 if usage_metadata else 0
        )
        total_tokens = (
            usage_metadata.total_token_count or (prompt_tokens + completion_tokens)
            if usage_metadata
            else 0
        )
        return LLMResponse(
            content="".join(chunks),
            role=MessageRole.ASSISTANT,
            provider=self.provider_id,
            model=target_model,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            raw_metadata={"streamed": True},
        )

    async def generate_stream(
        self, request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        """Gera texto do Gemini em partes sem aguardar a resposta completa."""
        async for response_chunk in self._generate_content_stream(request):
            if response_chunk.text:
                yield response_chunk.text

    async def _generate_content_stream(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[types.GenerateContentResponse, None]:
        """Abre o stream do SDK e normaliza erros de transporte/API."""
        client = self._ensure_client()
        target_model = request.model or self.default_model
        config = types.GenerateContentConfig(
            system_instruction=request.system_instruction,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )
        contents = self._convert_messages_to_contents(request.messages)
        if not contents:
            raise ProviderInvalidRequestError(
                "Nenhuma mensagem de usuário fornecida para a geração.",
                provider=self.provider_id,
            )

        try:
            stream = await client.aio.models.generate_content_stream(
                model=target_model,
                contents=contents,
                config=config,
            )
            async for response_chunk in stream:
                yield response_chunk
        except errors.APIError as exc:
            self._handle_api_error(exc)
        except Exception as exc:
            raise self._normalize_transport_error(exc) from exc

    def _handle_api_error(self, exc: errors.APIError) -> None:
        """Converte erros nativos do SDK em exceções canônicas de domínio."""
        err_msg = self._safe_error_details(exc)
        code = getattr(exc, "code", None)
        metadata = self._error_metadata(exc)
        retry_after = self._retry_after_seconds(exc, err_msg, metadata)
        request_id = getattr(exc, "request_id", None)
        if not request_id:
            headers = getattr(exc, "headers", None)
            if headers:
                request_id = headers.get("x-request-id") or headers.get("request-id")
        common = {
            "provider": self.provider_id,
            "details": self._safe_error_details(f"{err_msg} {metadata}"),
            "http_status": code if isinstance(code, int) else None,
            "retry_after_seconds": retry_after,
            "request_id": str(request_id) if request_id else None,
        }

        if code == 401 or "API_KEY_INVALID" in err_msg:
            raise ProviderAuthenticationError(
                "Autenticação falhou com a API Gemini.",
                **common,
            )
        if code == 403 or "PERMISSION_DENIED" in err_msg:
            raise ProviderAccessDeniedError(
                "Acesso negado pela API Gemini.",
                **common,
            )
        if code == 404 or "NOT_FOUND" in err_msg:
            raise ProviderNotFoundError(
                "O recurso solicitado não foi encontrado no Gemini.",
                **common,
            )
        if code == 429 or "RESOURCE_EXHAUSTED" in err_msg:
            raise ProviderRateLimitError(
                "Limite de utilização excedido no Gemini.",
                **common,
            )
        if code == 503 or "UNAVAILABLE" in err_msg:
            raise ProviderUnavailableError(
                "Serviço Gemini temporariamente indisponível.",
                **common,
            )
        if code in (500, 502, 504):
            raise LLMException(
                "Falha interna da API Gemini.",
                **common,
            )
        if code == 400 or "INVALID_ARGUMENT" in err_msg:
            raise ProviderInvalidRequestError(
                "Parâmetros de requisição inválidos para Gemini.",
                **common,
            )
        raise LLMException(
            "Falha não classificada na API Gemini.",
            **common,
        )

    def _safe_error_details(self, exc: BaseException | str) -> str:
        from app.utils.logging import SensitiveDataFilter

        details = SensitiveDataFilter.mask_sensitive_text(str(exc))
        if self._api_key:
            details = details.replace(self._api_key, "[MASCARADO]")
        return details

    @staticmethod
    def _error_metadata(exc: errors.APIError) -> str:
        metadata = getattr(exc, "details", None) or getattr(exc, "response_json", None)
        if metadata is None:
            return ""
        return str(metadata)

    @staticmethod
    def _retry_after_seconds(
        exc: errors.APIError,
        error_text: str,
        metadata: str,
    ) -> float | None:
        for attribute in ("retry_after_seconds", "retry_after", "retry_delay"):
            value = getattr(exc, attribute, None)
            if isinstance(value, (int, float)):
                return float(value)
            total_seconds = getattr(value, "total_seconds", None)
            if callable(total_seconds):
                return float(total_seconds())
        match = _RETRY_DELAY.search(f"{error_text} {metadata}")
        if not match:
            return None
        value = float(match.group("value"))
        unit = match.group("unit").lower()
        if unit.startswith("ms"):
            return value / 1000
        if unit.startswith("m"):
            return value * 60
        if unit.startswith("h"):
            return value * 3600
        return value

    def _normalize_transport_error(self, exc: Exception) -> LLMException:
        details = self._safe_error_details(exc)
        common = {"provider": self.provider_id, "details": details}
        if isinstance(exc, (TimeoutError,)):
            return ProviderTimeoutError(
                "Tempo limite excedido ao aguardar o Gemini.",
                **common,
            )
        if isinstance(exc, (ConnectionError, OSError)):
            return ProviderConnectionError(
                "Não foi possível conectar à API Gemini.",
                **common,
            )
        if isinstance(exc, (AttributeError, TypeError, ValueError)):
            return ProviderResponseError(
                "O Gemini retornou uma resposta inválida.",
                **common,
            )
        return LLMException(
            "Falha não classificada na API Gemini.",
            **common,
        )

    async def health_check(self) -> bool:
        """Verifica a integridade do provedor Gemini."""
        return bool(self._api_key and self._client)
