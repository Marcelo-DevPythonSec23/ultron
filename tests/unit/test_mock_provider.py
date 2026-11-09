"""Testes unitários para o MockProvider."""

import pytest

from app.intelligence.providers.base import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.intelligence.providers.mock import MockProvider
from app.models.message import ChatMessage, LLMRequest, MessageRole


@pytest.mark.asyncio
async def test_mock_provider_basic_generation():
    """Valida que o MockProvider responde de forma determinística."""
    provider = MockProvider()
    request = LLMRequest(
        messages=[
            ChatMessage(role=MessageRole.USER, content="Olá Ultron"),
        ],
        system_instruction="Seja prestativo",
    )

    response = await provider.generate_response(request)
    assert response.provider == "mock"
    assert response.role == MessageRole.ASSISTANT
    assert "Olá Ultron" in response.content
    assert response.usage.prompt_tokens > 0
    assert response.usage.completion_tokens > 0


@pytest.mark.asyncio
async def test_mock_provider_fixed_response():
    """Valida a resposta fixa configurada no MockProvider."""
    provider = MockProvider(fixed_response="Resposta customizada do mock")
    request = LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="Qualquer coisa")]
    )

    response = await provider.generate_response(request)
    assert response.content == "Resposta customizada do mock"


@pytest.mark.asyncio
async def test_mock_provider_simulated_errors():
    """Valida o disparo de erros canônicos simulados."""
    provider_auth = MockProvider(simulate_error="auth")
    req = LLMRequest(messages=[ChatMessage(role=MessageRole.USER, content="teste")])
    with pytest.raises(ProviderAuthenticationError):
        await provider_auth.generate_response(req)

    provider_rate = MockProvider(simulate_error="rate_limit")
    with pytest.raises(ProviderRateLimitError):
        await provider_rate.generate_response(req)

    provider_unavail = MockProvider(simulate_error="unavailable")
    with pytest.raises(ProviderUnavailableError):
        await provider_unavail.generate_response(req)


@pytest.mark.asyncio
async def test_mock_provider_health():
    """Valida a checagem de saúde do MockProvider."""
    p_ok = MockProvider()
    assert await p_ok.health_check() is True

    p_fail = MockProvider(simulate_error="unavailable")
    assert await p_fail.health_check() is False
