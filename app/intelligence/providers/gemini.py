"""Adaptador do provedor Google Gemini utilizando o SDK oficial google-genai."""

import logging

from google import genai
from google.genai import errors, types

from app.intelligence.providers.base import (
    LLMException,
    LLMProvider,
    ProviderAuthenticationError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
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

                logger.error("Erro da API Gemini: código=%s, msg=%s", exc.code, str(exc))
                self._handle_api_error(exc)
            except Exception as exc:
                if attempt < max_retries:
                    import asyncio
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                logger.error("Falha inesperada ao comunicar com Gemini: %s", str(exc))
                raise ProviderUnavailableError(
                    f"Erro de comunicação com Gemini: {exc!s}",
                    provider=self.provider_id,
                    details=str(exc),
                ) from exc

        if response is None:
            raise ProviderUnavailableError(
                "Não foi possível obter resposta do provedor Gemini após retentativas.",
                provider=self.provider_id,
            )

        # Extrair texto retornado
        content_text = response.text or ""

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

    def _handle_api_error(self, exc: errors.APIError) -> None:
        """Converte erros nativos do SDK em exceções canônicas de domínio."""
        err_msg = str(exc)
        code = getattr(exc, "code", None)

        if code in (401, 403) or "API_KEY_INVALID" in err_msg or "PERMISSION_DENIED" in err_msg:
            raise ProviderAuthenticationError(
                f"Autenticação falhou com a API Gemini: {err_msg}",
                provider=self.provider_id,
                details=err_msg,
            )
        if code == 429 or "RESOURCE_EXHAUSTED" in err_msg:
            raise ProviderRateLimitError(
                f"Limite de requisições excedido no Gemini: {err_msg}",
                provider=self.provider_id,
                details=err_msg,
            )
        if code in (500, 502, 503, 504) or "UNAVAILABLE" in err_msg:
            raise ProviderUnavailableError(
                f"Serviço Gemini temporariamente indisponível: {err_msg}",
                provider=self.provider_id,
                details=err_msg,
            )
        if code == 400 or "INVALID_ARGUMENT" in err_msg:
            raise ProviderInvalidRequestError(
                f"Parâmetros de requisição inválidos para Gemini: {err_msg}",
                provider=self.provider_id,
                details=err_msg,
            )
        raise LLMException(
            f"Erro na geração com Gemini: {err_msg}",
            provider=self.provider_id,
            details=err_msg,
        )

    async def health_check(self) -> bool:
        """Verifica a integridade do provedor Gemini."""
        return bool(self._api_key and self._client)
