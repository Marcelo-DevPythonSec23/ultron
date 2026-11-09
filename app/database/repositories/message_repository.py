"""Repositório para persistência e recuperação de mensagens históricas."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import MessageModel


class MessageRepository:
    """Encapsula operações de banco de dados para a entidade Message."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        raw_metadata: str | None = None,
    ) -> MessageModel:
        """Cria e persiste uma mensagem associada a uma conversa."""
        message = MessageModel(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_metadata=raw_metadata,
            created_at=datetime.now(UTC),
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_messages_by_conversation(
        self,
        conversation_id: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MessageModel]:
        """Recupera mensagens de uma conversa em ordem cronológica ascendente."""
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.asc())
        )
        if offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
