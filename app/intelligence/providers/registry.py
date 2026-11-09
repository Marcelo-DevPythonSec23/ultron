"""Registro e gerenciamento de provedores de LLM (Provider Registry)."""

import logging

from app.config import Settings, get_settings
from app.intelligence.providers.base import LLMException, LLMProvider
from app.intelligence.providers.gemini import GeminiProvider
from app.intelligence.providers.mock import MockProvider

logger = logging.getLogger("ultron.providers.registry")


class ProviderRegistry:
    """Catálogo centralizado de provedores de LLM suportados pelo ULTRON."""

    def __init__(self, default_provider_id: str = "gemini") -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._default_provider_id = default_provider_id

    def register_provider(self, provider: LLMProvider) -> None:
        """Registra uma instância de provedor no catálogo."""
        self._providers[provider.provider_id] = provider
        logger.info(
            "Provedor '%s' registrado com sucesso (modelo padrão: %s).",
            provider.provider_id,
            provider.default_model,
        )

    def get_provider(self, provider_id: str | None = None) -> LLMProvider:
        """Retorna o provedor solicitado ou o provedor padrão se None."""
        target_id = provider_id or self._default_provider_id
        if target_id not in self._providers:
            available = list(self._providers.keys())
            raise LLMException(
                f"Provedor de LLM '{target_id}' não encontrado. Disponíveis: {available}",
                provider=target_id,
            )
        return self._providers[target_id]

    def list_providers(self) -> list[str]:
        """Lista os IDs de todos os provedores registrados."""
        return list(self._providers.keys())

    @property
    def default_provider_id(self) -> str:
        return self._default_provider_id


def create_default_registry(settings: Settings | None = None) -> ProviderRegistry:
    """Cria e inicializa o registro de provedores padrão da aplicação."""
    cfg = settings or get_settings()
    registry = ProviderRegistry(default_provider_id=cfg.DEFAULT_LLM_PROVIDER)

    # Registrar provedor Mock sempre disponível
    registry.register_provider(MockProvider())

    # Registrar provedor Gemini
    gemini_key = cfg.get_gemini_api_key()
    registry.register_provider(
        GeminiProvider(
            api_key=gemini_key,
            default_model=cfg.GEMINI_DEFAULT_MODEL,
        )
    )

    return registry


_global_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Retorna uma instância global singleton do registro de provedores."""
    global _global_registry
    if _global_registry is None:
        _global_registry = create_default_registry()
    return _global_registry
