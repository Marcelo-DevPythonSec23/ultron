"""Testes unitários para o Orchestrator."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chat_service import ChatService
from app.core.context_manager import ContextManager
from app.core.orchestrator import Orchestrator
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.message_repository import MessageRepository
from app.intelligence.prompt_engine import PromptEngine
from app.intelligence.providers.mock import MockProvider
from app.intelligence.providers.registry import ProviderRegistry
from app.models.conversation import ChatRequest
from app.models.message import MessageRole


@pytest.mark.asyncio
async def test_orchestrator_end_to_end_flow(test_session: AsyncSession):
    """Valida o ciclo completo de orquestração com MockProvider."""
    conv_repo = ConversationRepository(test_session)
    msg_repo = MessageRepository(test_session)
    chat_service = ChatService(conv_repo, msg_repo)
    context_manager = ContextManager()
    prompt_engine = PromptEngine()

    registry = ProviderRegistry(default_provider_id="mock")
    mock_provider = MockProvider(fixed_response="Resposta orquestrada com sucesso.")
    registry.register_provider(mock_provider)

    orchestrator = Orchestrator(
        chat_service=chat_service,
        context_manager=context_manager,
        prompt_engine=prompt_engine,
        provider_registry=registry,
    )

    request = ChatRequest(
        message="Olá Ultron, inicie o ciclo.",
        provider="mock",
    )

    response = await orchestrator.process_chat(request)

    assert response.conversation_id is not None
    assert response.role == MessageRole.ASSISTANT
    assert response.content == "Resposta orquestrada com sucesso."
    assert response.provider == "mock"

    # Verificar se as 2 mensagens (user e assistant) foram salvas no histórico
    history = await chat_service.get_recent_chat_messages(response.conversation_id)
    assert len(history) == 2
    assert history[0].role == MessageRole.USER
    assert history[1].role == MessageRole.ASSISTANT


@pytest.mark.asyncio
async def test_orchestrator_streams_response_and_preserves_usage(
    test_session: AsyncSession,
):
    """Valida o streaming na CLI e a persistência da resposta completa."""
    conv_repo = ConversationRepository(test_session)
    msg_repo = MessageRepository(test_session)
    chat_service = ChatService(conv_repo, msg_repo)
    registry = ProviderRegistry(default_provider_id="mock")
    registry.register_provider(MockProvider(fixed_response="Streaming concluído."))
    orchestrator = Orchestrator(
        chat_service=chat_service,
        context_manager=ContextManager(),
        prompt_engine=PromptEngine(),
        provider_registry=registry,
    )
    chunks: list[str] = []

    response = await orchestrator.process_chat(
        ChatRequest(message="Inicie o streaming.", provider="mock"),
        on_chunk=chunks.append,
    )

    assert "".join(chunks) == response.content == "Streaming concluído."
    assert response.usage.completion_tokens > 0
    history = await chat_service.get_recent_chat_messages(response.conversation_id)
    assert [message.content for message in history] == [
        "Inicie o streaming.",
        "Streaming concluído.",
    ]
