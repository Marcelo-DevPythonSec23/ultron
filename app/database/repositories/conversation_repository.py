"""Repositório para persistência e recuperação de conversas."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import ConversationModel, MessageModel


class ConversationRepository:
    """Encapsula operações de banco de dados para a entidade Conversation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, conversation_id: str) -> ConversationModel | None:
        """Busca uma conversa pelo UUID."""
        stmt = (
            select(ConversationModel)
            .options(selectinload(ConversationModel.messages))
            .where(ConversationModel.id == conversation_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        conversation_id: str,
        title: str = "Nova Conversa",
        provider: str = "gemini",
        model: str = "gemini-2.5-flash",
        system_override: str | None = None,
    ) -> ConversationModel:
        """Cria e persiste uma nova conversa."""
        conversation = ConversationModel(
            id=conversation_id,
            title=title,
            provider=provider,
            model=model,
            system_override=system_override,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def update_timestamp_and_title(
        self, conversation_id: str, title: str | None = None
    ) -> None:
        """Atualiza a data da última interação e opcionalmente o título."""
        conv = await self.get_by_id(conversation_id)
        if conv:
            conv.updated_at = datetime.now(UTC)
            if title and conv.title == "Nova Conversa":
                conv.title = title[:100]
            await self.session.commit()

    async def list_conversations(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[tuple[ConversationModel, int]], int]:
        """Lista conversas com contagem de mensagens e paginação."""
        count_stmt = select(func.count()).select_from(ConversationModel)
        total_count = (await self.session.execute(count_stmt)).scalar() or 0

        list_stmt = (
            select(ConversationModel, func.count(MessageModel.id).label("msg_count"))
            .outerjoin(MessageModel, ConversationModel.id == MessageModel.conversation_id)
            .group_by(ConversationModel.id)
            .order_by(ConversationModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(list_stmt)
        items = [(row[0], int(row[1])) for row in result.all()]

        return items, total_count
