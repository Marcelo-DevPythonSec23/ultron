"""Mecanismo de montagem de prompts (Prompt Engine) para o ULTRON."""

import logging

from app.intelligence.personality.personality_config import PersonalityConfig
from app.models.message import ChatMessage, LLMRequest, MessageRole

logger = logging.getLogger("ultron.prompt_engine")


class PromptEngine:
    """Responsável por compor as instruções de sistema, contexto e requisições ao LLM."""

    def __init__(self, personality: PersonalityConfig | None = None) -> None:
        self.personality = personality or PersonalityConfig()

    def assemble_request(
        self,
        messages: list[ChatMessage],
        system_instruction_override: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMRequest:
        """Monta a solicitação estruturada para o provedor de LLM."""
        # Resolver a instrução de sistema
        if system_instruction_override and system_instruction_override.strip():
            system_instruction = system_instruction_override.strip()
        else:
            system_instruction = self.personality.render_system_prompt()

        # Filtrar mensagens garantindo que não haja conteúdo nulo
        sanitized_messages: list[ChatMessage] = []
        for msg in messages:
            # Mensagens de papel de sistema no histórico são consolidadas na system_instruction
            if msg.role == MessageRole.SYSTEM:
                system_instruction += f"\n\nContexto Adicional:\n{msg.content}"
            else:
                sanitized_messages.append(msg)

        final_temp = 0.7 if temperature is None else temperature

        return LLMRequest(
            messages=sanitized_messages,
            system_instruction=system_instruction,
            model=model,
            temperature=final_temp,
            max_output_tokens=max_output_tokens,
        )
