"""Módulo de repositórios para acesso a dados."""

from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.message_repository import MessageRepository

__all__ = ["ConversationRepository", "MessageRepository"]
