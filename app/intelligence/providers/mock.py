"""Provedor simulado (Mock) para testes automatizados e ambientes offline."""

import logging

from app.intelligence.providers.base import (
    LLMProvider,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.models.message import LLMRequest, LLMResponse, LLMUsage, MessageRole

logger = logging.getLogger("ultron.providers.mock")


class MockProvider(LLMProvider):
    """Implementação simulada do LLMProvider que não consome rede nem cotas reais."""

    def __init__(
        self,
        default_model: str = "mock-model-v1",
        fixed_response: str | None = None,
        simulate_error: str | None = None,
    ) -> None:
        self._default_model = default_model
        self.fixed_response = fixed_response
        self.simulate_error = simulate_error
        self.invocation_count = 0
        self.last_request: LLMRequest | None = None

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return self._default_model

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Gera uma resposta simulada baseada na última mensagem ou em resposta fixa."""
        self.invocation_count += 1
        self.last_request = request

        # Simular erros controlados para testes de resiliência
        if self.simulate_error == "auth":
            raise ProviderAuthenticationError(
                "Chave de autenticação mock inválida.", provider=self.provider_id
            )
        if self.simulate_error == "rate_limit":
            raise ProviderRateLimitError(
                "Limite de taxa mock excedido.", provider=self.provider_id
            )
        if self.simulate_error == "unavailable":
            raise ProviderUnavailableError(
                "Serviço mock temporariamente indisponível.", provider=self.provider_id
            )

        # Determinar conteúdo da resposta
        if self.fixed_response:
            content = self.fixed_response
        else:
            last_user_msg = ""
            for m in reversed(request.messages):
                if m.role == MessageRole.USER:
                    last_user_msg = m.content
                    break
            content = f"[Resposta Simulada ULTRON] Você disse: '{last_user_msg}'"

        # Simulação simples de contagem de tokens (aproximadamente 4 caracteres por token)
        total_chars_in = sum(len(m.content) for m in request.messages)
        if request.system_instruction:
            total_chars_in += len(request.system_instruction)

        prompt_tokens = max(1, total_chars_in // 4)
        completion_tokens = max(1, len(content) // 4)

        return LLMResponse(
            content=content,
            role=MessageRole.ASSISTANT,
            provider=self.provider_id,
            model=request.model or self.default_model,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            raw_metadata={"mock": True, "invocation": self.invocation_count},
        )

    async def health_check(self) -> bool:
        """Sempre retorna True a menos que simulate_error seja 'unavailable'."""
        return self.simulate_error != "unavailable"
