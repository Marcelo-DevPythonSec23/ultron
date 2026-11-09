"""Gerenciador de contexto conversacional e controle de janelas de tokens."""

import logging

from app.models.message import ChatMessage

logger = logging.getLogger("ultron.core.context_manager")


class ContextManager:
    """Aplica políticas de retenção de histórico e limitação de tokens para a janela de contexto."""

    def __init__(self, max_tokens: int = 4096, max_messages: int = 20) -> None:
        self.max_tokens = max_tokens
        self.max_messages = max_messages

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Aproximação heurística de contagem de tokens (~4 caracteres por token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def estimate_message_tokens(self, message: ChatMessage) -> int:
        """Estima o custo em tokens de uma mensagem única."""
        return self.estimate_tokens(message.content) + 4  # Margem para metadados de papel

    def build_context(
        self,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
        max_messages: int | None = None,
    ) -> list[ChatMessage]:
        """Seleciona as mensagens mais recentes que respeitam os limites de contagem e tokens."""
        effective_max_messages = max_messages if max_messages is not None else self.max_messages
        effective_max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        if not messages:
            return []

        # 1. Aplicar filtro de quantidade de mensagens (preservando as mais recentes)
        candidates = messages[-effective_max_messages:]

        # 2. Acumular de trás para frente (da mais recente para a mais antiga) respeitando tokens
        selected: list[ChatMessage] = []
        accumulated_tokens = 0

        for msg in reversed(candidates):
            msg_tokens = self.estimate_message_tokens(msg)
            if accumulated_tokens + msg_tokens > effective_max_tokens:
                # Se exceder o limite de tokens, não inclui mensagens anteriores
                logger.debug(
                    "Limite de tokens atingido (%d > %d). Truncando histórico.",
                    accumulated_tokens + msg_tokens,
                    effective_max_tokens,
                )
                break

            selected.append(msg)
            accumulated_tokens += msg_tokens

        # Se mesmo a mensagem mais recente exceder sozinha o limite, incluí-la para permitir tentativa
        if not selected and candidates:
            selected.append(candidates[-1])

        # Restaurar a ordem cronológica original (mais antiga -> mais recente)
        selected.reverse()
        return selected
