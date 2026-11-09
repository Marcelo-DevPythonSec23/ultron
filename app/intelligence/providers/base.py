"""Interface base abstrata para Provedores de Modelos de Linguagem (LLM)."""

from abc import ABC, abstractmethod

from app.models.message import LLMRequest, LLMResponse


class LLMException(Exception):
    """Exceção base para falhas na camada de inteligência e provedores."""

    def __init__(self, message: str, provider: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.details = details


class ProviderAuthenticationError(LLMException):
    """Lançada quando a chave de API ou credencial do provedor é inválida ou ausente."""


class ProviderRateLimitError(LLMException):
    """Lançada quando a cota ou limite de taxa do provedor foi excedido."""


class ProviderUnavailableError(LLMException):
    """Lançada quando o provedor está fora do ar, inacessível ou respondeu timeout."""


class ProviderInvalidRequestError(LLMException):
    """Lançada quando a requisição ao provedor é rejeitada por parâmetros inválidos."""


class LLMProvider(ABC):
    """Contrato abstrato que todo provedor de modelo deve implementar."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Identificador textual único do provedor (ex: 'gemini', 'mock')."""

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Modelo padrão utilizado por este provedor se nenhum for especificado."""

    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Executa a chamada assíncrona ao modelo e retorna uma resposta estruturada."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica a conectividade e disponibilidade do provedor."""
