"""Testes unitários para o GeminiProvider com chamadas mockadas."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import errors

from app.intelligence.providers.base import (
    LLMException,
    ProviderAccessDeniedError,
    ProviderAuthenticationError,
    ProviderInvalidRequestError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.intelligence.providers.gemini import GeminiProvider
from app.models.message import ChatMessage, LLMRequest, MessageRole


@pytest.mark.asyncio
async def test_gemini_provider_missing_key_raises_auth_error():
    """Valida que o provedor falha com ProviderAuthenticationError sem chave configurada."""
    provider = GeminiProvider(api_key=None)
    req = LLMRequest(messages=[ChatMessage(role=MessageRole.USER, content="olá")])
    with pytest.raises(ProviderAuthenticationError):
        await provider.generate_response(req)


@pytest.mark.asyncio
async def test_gemini_provider_empty_messages_raises_invalid_request():
    """Valida que requisição sem mensagens de usuário é rejeitada."""
    provider = GeminiProvider(api_key="fake-key")
    req = LLMRequest(
        messages=[ChatMessage(role=MessageRole.SYSTEM, content="apenas sistema")]
    )
    with pytest.raises(ProviderInvalidRequestError):
        await provider.generate_response(req)


@pytest.mark.asyncio
async def test_gemini_provider_success():
    """Valida a chamada bem sucedida e conversão de tokens com client mockado."""
    provider = GeminiProvider(api_key="fake-key", default_model="gemini-2.5-flash")

    # Mockar a resposta da API Gemini
    mock_resp = MagicMock()
    mock_resp.text = "Resposta oficial do Gemini"
    mock_resp.usage_metadata.prompt_token_count = 15
    mock_resp.usage_metadata.candidates_token_count = 25
    mock_resp.usage_metadata.total_token_count = 40
    mock_resp.model_version = "v2.5"

    provider._client = MagicMock()
    provider._client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

    req = LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="Olá!")],
        system_instruction="Você é o Ultron",
        temperature=0.5,
    )

    resp = await provider.generate_response(req)
    assert resp.provider == "gemini"
    assert resp.content == "Resposta oficial do Gemini"
    assert resp.usage.prompt_tokens == 15
    assert resp.usage.completion_tokens == 25
    assert resp.usage.total_tokens == 40


@pytest.mark.asyncio
async def test_gemini_provider_streaming_response_preserves_chunks_and_usage():
    """Valida o streaming real do Gemini e as métricas da resposta final."""
    provider = GeminiProvider(api_key="fake-key", default_model="gemini-2.5-flash")
    usage = MagicMock(
        prompt_token_count=12,
        candidates_token_count=8,
        total_token_count=20,
    )

    async def response_chunks():
        yield MagicMock(text="Resposta ", usage_metadata=None)
        yield MagicMock(text="progressiva.", usage_metadata=usage)

    provider._client = MagicMock()
    provider._client.aio.models.generate_content_stream = AsyncMock(
        return_value=response_chunks()
    )
    request = LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="Olá")],
    )
    chunks: list[str] = []

    response = await provider.generate_response_streaming(request, chunks.append)

    assert chunks == ["Resposta ", "progressiva."]
    assert response.content == "Resposta progressiva."
    assert response.usage.prompt_tokens == 12
    assert response.usage.completion_tokens == 8
    assert response.usage.total_tokens == 20
    provider._client.aio.models.generate_content_stream.assert_awaited_once()


@pytest.mark.asyncio
async def test_gemini_provider_error_normalization():
    """Valida a normalização de erros nativos da API do Gemini."""
    provider = GeminiProvider(api_key="fake-key")
    provider._client = MagicMock()

    req = LLMRequest(messages=[ChatMessage(role=MessageRole.USER, content="teste")])

    # 401 / Auth Error
    provider._client.aio.models.generate_content = AsyncMock(
        side_effect=errors.APIError(401, "API_KEY_INVALID")
    )
    with pytest.raises(ProviderAuthenticationError):
        await provider.generate_response(req)

    # 429 / Rate Limit
    provider._client.aio.models.generate_content = AsyncMock(
        side_effect=errors.APIError(429, "RESOURCE_EXHAUSTED")
    )
    with pytest.raises(ProviderRateLimitError):
        await provider.generate_response(req)

    # 503 / Unavailable
    provider._client.aio.models.generate_content = AsyncMock(
        side_effect=errors.APIError(503, "UNAVAILABLE")
    )
    with pytest.raises(ProviderUnavailableError):
        await provider.generate_response(req)


@pytest.mark.parametrize(
    ("status", "message", "exception_type"),
    [
        (401, "API_KEY_INVALID", ProviderAuthenticationError),
        (403, "PERMISSION_DENIED", ProviderAccessDeniedError),
        (404, "NOT_FOUND", ProviderNotFoundError),
        (429, "RESOURCE_EXHAUSTED", ProviderRateLimitError),
        (500, "INTERNAL", LLMException),
        (503, "UNAVAILABLE", ProviderUnavailableError),
    ],
)
def test_gemini_maps_http_errors_without_exposing_provider_payload(
    status,
    message,
    exception_type,
):
    provider = GeminiProvider(api_key="private-api-key")

    with pytest.raises(exception_type) as exc_info:
        provider._handle_api_error(
            errors.APIError(
                status,
                f'{{"status":"{message}","api_key":"private-api-key"}}',
            )
        )

    assert exc_info.value.http_status == status
    assert "private-api-key" not in exc_info.value.message
    assert message not in exc_info.value.message
    assert "private-api-key" not in (exc_info.value.details or "")
    assert "[MASCARADO]" in (exc_info.value.details or "")


def test_gemini_extracts_retry_delay_from_sdk_error_metadata():
    provider = GeminiProvider(api_key="fake-key")

    with pytest.raises(ProviderRateLimitError) as exc_info:
        provider._handle_api_error(
            errors.APIError(
                429,
                '{"message":"GenerateRequestsPerDay exceeded",'
                '"details":[{"retryDelay":"90s"}]}',
            )
        )

    assert exc_info.value.retry_after_seconds == 90
    assert "GenerateRequestsPerDay" in exc_info.value.details


@pytest.mark.asyncio
async def test_gemini_does_not_retry_rate_limit_response():
    provider = GeminiProvider(api_key="fake-key")
    provider._client = MagicMock()
    request = LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="quota test")]
    )
    provider._client.aio.models.generate_content = AsyncMock(
        side_effect=errors.APIError(
            429,
            '{"error":{"status":"RESOURCE_EXHAUSTED","api_key":"private-value"}}',
        )
    )

    with pytest.raises(ProviderRateLimitError):
        await provider.generate_response(request)

    provider._client.aio.models.generate_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_gemini_rejects_malformed_response_safely():
    provider = GeminiProvider(api_key="fake-key")
    provider._client = MagicMock()
    provider._client.aio.models.generate_content = AsyncMock(return_value=None)
    request = LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="invalid response")]
    )

    with pytest.raises(ProviderResponseError):
        await provider.generate_response(request)
