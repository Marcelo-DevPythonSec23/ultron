"""Dependências injetáveis do FastAPI para injeção de serviços e repositórios."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.chat_service import ChatService
from app.core.context_manager import ContextManager
from app.core.orchestrator import Orchestrator
from app.database.connection import get_db_session
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.message_repository import MessageRepository
from app.intelligence.prompt_engine import PromptEngine
from app.intelligence.providers.registry import ProviderRegistry, get_provider_registry

# Injeção de configurações e sessão de banco
SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_conversation_repository(session: DBSessionDep) -> ConversationRepository:
    """Injeta instância de ConversationRepository."""
    return ConversationRepository(session)


def get_message_repository(session: DBSessionDep) -> MessageRepository:
    """Injeta instância de MessageRepository."""
    return MessageRepository(session)


def get_chat_service(
    conv_repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    msg_repo: Annotated[MessageRepository, Depends(get_message_repository)],
) -> ChatService:
    """Injeta instância de ChatService."""
    return ChatService(conversation_repo=conv_repo, message_repo=msg_repo)


def get_context_manager(settings: SettingsDep) -> ContextManager:
    """Injeta instância de ContextManager com base nas configurações."""
    return ContextManager(
        max_tokens=settings.MAX_CONTEXT_TOKENS,
        max_messages=settings.MAX_HISTORY_MESSAGES,
    )


def get_prompt_engine() -> PromptEngine:
    """Injeta instância do mecanismo de prompts."""
    return PromptEngine()


def get_orchestrator(
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    context_manager: Annotated[ContextManager, Depends(get_context_manager)],
    prompt_engine: Annotated[PromptEngine, Depends(get_prompt_engine)],
    registry: Annotated[ProviderRegistry, Depends(get_provider_registry)],
) -> Orchestrator:
    """Injeta o orquestrador conversacional completo."""
    return Orchestrator(
        chat_service=chat_service,
        context_manager=context_manager,
        prompt_engine=prompt_engine,
        provider_registry=registry,
    )


OrchestratorDep = Annotated[Orchestrator, Depends(get_orchestrator)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
