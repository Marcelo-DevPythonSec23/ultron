"""Interface base abstrata para Provedores de Modelos de Linguagem (LLM)."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable

from app.models.message import LLMRequest, LLMResponse


class LLMException(Exception):
    """Exceção base para falhas na camada de inteligência e provedores."""

    def __init__(
        self,
        message: str,
        provider: str,
        details: str | None = None,
        *,
        http_status: int | None = None,
        retry_after_seconds: float | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.details = details
        self.http_status = http_status
        self.retry_after_seconds = retry_after_seconds
        self.request_id = request_id


class ProviderAuthenticationError(LLMException):
    """Lançada quando a chave de API ou credencial do provedor é inválida ou ausente."""


class ProviderRateLimitError(LLMException):
    """Lançada quando a cota ou limite de taxa do provedor foi excedido."""


class ProviderUnavailableError(LLMException):
    """Lançada quando o provedor está fora do ar, inacessível ou respondeu timeout."""


class ProviderInvalidRequestError(LLMException):
    """Lançada quando a requisição ao provedor é rejeitada por parâmetros inválidos."""


class ProviderAccessDeniedError(LLMException):
    """Lançada quando o provedor nega acesso ao recurso."""


class ProviderNotFoundError(LLMException):
    """Lançada quando o recurso solicitado não existe."""


class ProviderTimeoutError(LLMException):
    """Lançada quando o provedor excede o tempo de resposta."""


class ProviderConnectionError(LLMException):
    """Lançada quando não é possível estabelecer conexão com o provedor."""


class ProviderResponseError(LLMException):
    """Lançada quando o provedor retorna uma resposta inválida."""


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
    async def generate_stream(
        self, request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        """Gera e transmite pedaços de texto (tokens/chunks) assincronamente."""

    async def generate_response_streaming(
        self,
        request: LLMRequest,
        on_chunk: Callable[[str], None],
    ) -> LLMResponse:
        """Consome o stream e retorna uma resposta canônica para provedores compatíveis."""
        chunks: list[str] = []
        async for chunk in self.generate_stream(request):
            chunks.append(chunk)
            on_chunk(chunk)

        return LLMResponse(
            content="".join(chunks),
            provider=self.provider_id,
            model=request.model or self.default_model,
        )

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica a conectividade e disponibilidade do provedor."""
