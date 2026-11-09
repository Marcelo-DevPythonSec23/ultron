"""Testes unitários para o ProviderRegistry."""

import pytest

from app.config import Settings
from app.intelligence.providers.base import LLMException
from app.intelligence.providers.mock import MockProvider
from app.intelligence.providers.registry import (
    ProviderRegistry,
    create_default_registry,
)


def test_registry_registration_and_lookup():
    """Valida o registro e recuperação de provedores."""
    registry = ProviderRegistry(default_provider_id="mock")
    mock_p = MockProvider(default_model="mock-1")
    registry.register_provider(mock_p)

    # Buscar pelo nome
    assert registry.get_provider("mock") is mock_p
    # Buscar default
    assert registry.get_provider() is mock_p
    # Listar
    assert "mock" in registry.list_providers()


def test_registry_unknown_provider_raises():
    """Valida que provedor desconhecido lança LLMException explicativa."""
    registry = ProviderRegistry(default_provider_id="mock")
    with pytest.raises(LLMException) as exc_info:
        registry.get_provider("openai_inexistente")
    assert "não encontrado" in str(exc_info.value)


def test_create_default_registry():
    """Valida que create_default_registry registra gemini e mock."""
    settings = Settings(
        DEFAULT_LLM_PROVIDER="mock",
        GEMINI_API_KEY="fake-key",  # type: ignore
    )
    reg = create_default_registry(settings)
    assert "gemini" in reg.list_providers()
    assert "mock" in reg.list_providers()
    assert reg.default_provider_id == "mock"
