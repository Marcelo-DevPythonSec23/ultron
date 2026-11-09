"""Testes unitários para o ChatService e persistência relacional."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chat_service import ChatService
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.message_repository import MessageRepository
from app.models.message import MessageRole


@pytest.mark.asyncio
async def test_chat_service_create_and_retrieve_conversation(test_session: AsyncSession):
    """Valida a criação e recuperação de conversas e mensagens."""
    conv_repo = ConversationRepository(test_session)
    msg_repo = MessageRepository(test_session)
    service = ChatService(conv_repo, msg_repo)

    # 1. Criar conversa
    conv = await service.get_or_create_conversation(
        provider="mock",
        model="mock-v1",
        system_override="Instrução customizada",
    )
    assert conv.id is not None
    assert conv.provider == "mock"

    # 2. Registrar mensagem de usuário
    user_msg = await service.record_user_message(conv.id, "Qual o significado da vida?")
    assert user_msg.id is not None
    assert user_msg.role == MessageRole.USER.value

    # 3. Registrar resposta do assistente
    asst_msg = await service.record_assistant_message(
        conversation_id=conv.id,
        content="42",
        provider="mock",
        model="mock-v1",
        prompt_tokens=10,
        completion_tokens=2,
    )
    assert asst_msg.id is not None
    assert asst_msg.role == MessageRole.ASSISTANT.value

    # 4. Recuperar histórico de mensagens canônicas
    history = await service.get_recent_chat_messages(conv.id)
    assert len(history) == 2
    assert history[0].role == MessageRole.USER
    assert history[1].role == MessageRole.ASSISTANT

    # 5. Listar conversas
    summaries, total = await service.list_conversations()
    assert total == 1
    assert summaries[0].id == conv.id
    assert summaries[0].message_count == 2
