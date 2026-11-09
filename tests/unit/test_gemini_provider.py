"""Testes unitários para o GeminiProvider com chamadas mockadas."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import errors

from app.intelligence.providers.base import (
    ProviderAuthenticationError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
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
