"""Orquestrador do ciclo completo de processamento de mensagens no ULTRON."""

import logging

from app.core.chat_service import ChatService
from app.core.context_manager import ContextManager
from app.intelligence.prompt_engine import PromptEngine
from app.intelligence.providers.registry import ProviderRegistry
from app.models.conversation import ChatRequest, ChatResponse
from app.models.message import LLMUsage, MessageRole

logger = logging.getLogger("ultron.core.orchestrator")


class Orchestrator:
    """Coordena todas as etapas do ciclo conversacional: persistência, contexto, prompt e IA."""

    def __init__(
        self,
        chat_service: ChatService,
        context_manager: ContextManager,
        prompt_engine: PromptEngine,
        provider_registry: ProviderRegistry,
    ) -> None:
        self.chat_service = chat_service
        self.context_manager = context_manager
        self.prompt_engine = prompt_engine
        self.provider_registry = provider_registry

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """Processa a mensagem do usuário ponta a ponta e retorna a resposta do assistente."""
        # 1. Determinar provedor e modelo
        target_provider_id = request.provider or self.provider_registry.default_provider_id
        provider = self.provider_registry.get_provider(target_provider_id)
        target_model = request.model or provider.default_model

        # 2. Obter ou criar conversa
        conversation = await self.chat_service.get_or_create_conversation(
            conversation_id=request.conversation_id,
            provider=target_provider_id,
            model=target_model,
            system_override=request.system_instruction_override,
        )
        conversation_id = conversation.id

        # 3. Persistir mensagem de entrada do usuário
        await self.chat_service.record_user_message(
            conversation_id=conversation_id,
            content=request.message,
        )

        # 4. Recuperar histórico recente de mensagens da conversa
        all_messages = await self.chat_service.get_recent_chat_messages(
            conversation_id=conversation_id,
            limit=self.context_manager.max_messages,
        )

        # 5. Filtrar e truncar mensagens com base na janela de tokens e políticas de contexto
        context_messages = self.context_manager.build_context(
            messages=all_messages,
            max_tokens=self.context_manager.max_tokens,
        )

        # 6. Montar o prompt e instruções de sistema via PromptEngine
        effective_system_instruction = (
            request.system_instruction_override
            or conversation.system_override
        )
        llm_request = self.prompt_engine.assemble_request(
            messages=context_messages,
            system_instruction_override=effective_system_instruction,
            model=target_model,
            temperature=request.temperature,
        )

        # 7. Despachar para o provedor de LLM
        logger.info(
            "Despachando geração para provedor='%s', modelo='%s' (conversa=%s)",
            provider.provider_id,
            target_model,
            conversation_id,
        )
        llm_response = await provider.generate_response(llm_request)

        # 8. Persistir a resposta gerada pelo assistente
        assistant_msg_record = await self.chat_service.record_assistant_message(
            conversation_id=conversation_id,
            content=llm_response.content,
            provider=llm_response.provider,
            model=llm_response.model,
            prompt_tokens=llm_response.usage.prompt_tokens,
            completion_tokens=llm_response.usage.completion_tokens,
            metadata=llm_response.raw_metadata,
        )

        # 9. Retornar resposta estruturada para a API
        return ChatResponse(
            conversation_id=conversation_id,
            message_id=assistant_msg_record.id,
            role=MessageRole.ASSISTANT,
            content=llm_response.content,
            provider=llm_response.provider,
            model=llm_response.model,
            usage=llm_response.usage or LLMUsage(),
            created_at=assistant_msg_record.created_at,
        )
