"""Serviço de gerenciamento de sessões conversacionais e mensagens."""

import json
import logging
import uuid

from app.database.models import ConversationModel, MessageModel
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.message_repository import MessageRepository
from app.models.conversation import ConversationSummary, MessageItem
from app.models.message import ChatMessage, MessageRole

logger = logging.getLogger("ultron.core.chat_service")


class ChatService:
    """Responsável por gerenciar o ciclo de vida de conversas e mensagens."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
    ) -> None:
        self.conv_repo = conversation_repo
        self.msg_repo = message_repo

    async def get_or_create_conversation(
        self,
        conversation_id: str | None = None,
        provider: str = "gemini",
        model: str = "gemini-2.5-flash",
        system_override: str | None = None,
        initial_title: str | None = None,
    ) -> ConversationModel:
        """Busca uma conversa existente ou cria uma nova com ID gerado."""
        if conversation_id:
            conv = await self.conv_repo.get_by_id(conversation_id)
            if conv:
                return conv
            # Se ID foi fornecido mas não existe, cria com esse mesmo ID
            target_id = conversation_id
        else:
            target_id = str(uuid.uuid4())

        title = initial_title or "Nova Conversa"
        logger.info("Criando nova conversa ID: %s", target_id)
        return await self.conv_repo.create(
            conversation_id=target_id,
            title=title,
            provider=provider,
            model=model,
            system_override=system_override,
        )

    async def record_user_message(
        self,
        conversation_id: str,
        content: str,
    ) -> MessageModel:
        """Registra a mensagem de entrada do usuário."""
        msg_id = str(uuid.uuid4())
        msg = await self.msg_repo.create_message(
            message_id=msg_id,
            conversation_id=conversation_id,
            role=MessageRole.USER.value,
            content=content,
        )
        # Atualizar timestamp da conversa e inferir título se for a primeira mensagem
        title_hint = content.strip().split("\n")[0][:60]
        await self.conv_repo.update_timestamp_and_title(conversation_id, title=title_hint)
        return msg

    async def record_assistant_message(
        self,
        conversation_id: str,
        content: str,
        provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        metadata: dict | None = None,
    ) -> MessageModel:
        """Registra a resposta gerada pelo assistente."""
        msg_id = str(uuid.uuid4())
        raw_metadata = json.dumps(metadata) if metadata else None
        msg = await self.msg_repo.create_message(
            message_id=msg_id,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT.value,
            content=content,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_metadata=raw_metadata,
        )
        await self.conv_repo.update_timestamp_and_title(conversation_id)
        return msg

    async def get_recent_chat_messages(
        self, conversation_id: str, limit: int = 20
    ) -> list[ChatMessage]:
        """Recupera mensagens históricas como objetos canônicos ChatMessage."""
        models = await self.msg_repo.get_messages_by_conversation(
            conversation_id=conversation_id, limit=limit
        )
        return [
            ChatMessage(
                role=MessageRole(m.role),
                content=m.content,
                created_at=m.created_at,
            )
            for m in models
        ]

    async def get_conversation_history_items(
        self, conversation_id: str
    ) -> list[MessageItem]:
        """Recupera o histórico para a API."""
        models = await self.msg_repo.get_messages_by_conversation(conversation_id)
        return [
            MessageItem(
                id=m.id,
                role=MessageRole(m.role),
                content=m.content,
                provider=m.provider,
                model=m.model,
                created_at=m.created_at,
            )
            for m in models
        ]

    async def list_conversations(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[ConversationSummary], int]:
        """Lista sumários de conversas."""
        items, total = await self.conv_repo.list_conversations(limit=limit, offset=offset)
        summaries = [
            ConversationSummary(
                id=c.id,
                title=c.title,
                provider=c.provider,
                model=c.model,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=msg_count,
            )
            for c, msg_count in items
        ]
        return summaries, total
