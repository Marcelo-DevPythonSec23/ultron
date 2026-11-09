"""Modelos de dados para conversas e transferências na API REST."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.models.message import LLMUsage, MessageRole


class ChatRequest(BaseModel):
    """Payload de entrada para a rota POST /api/v1/chat."""

    conversation_id: str | None = Field(
        default=None,
        description="Identificador UUID da conversa. Se omitido, uma nova conversa será criada.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=32000,
        description="Mensagem enviada pelo usuário.",
    )
    provider: str | None = Field(
        default=None,
        description="Sobrescrita opcional do provedor (ex: gemini, mock).",
    )
    model: str | None = Field(
        default=None,
        description="Sobrescrita opcional do modelo a ser utilizado.",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sobrescrita opcional do parâmetro de criatividade.",
    )
    system_instruction_override: str | None = Field(
        default=None,
        description="Sobrescrita opcional da personalidade/instruções de sistema.",
    )


class ChatResponse(BaseModel):
    """Payload de saída retornado com sucesso pela rota POST /api/v1/chat."""

    conversation_id: str
    message_id: str
    role: MessageRole = MessageRole.ASSISTANT
    content: str
    provider: str
    model: str
    usage: LLMUsage
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageItem(BaseModel):
    """Item resumido de mensagem em consultas de histórico."""

    id: str
    role: MessageRole
    content: str
    provider: str | None = None
    model: str | None = None
    created_at: datetime


class ConversationSummary(BaseModel):
    """Sumário de conversa para listagens paginadas."""

    id: str
    title: str
    provider: str
    model: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationListResponse(BaseModel):
    """Resposta de listagem de conversas com totalização."""

    total: int
    items: list[ConversationSummary]


class ConversationHistoryResponse(BaseModel):
    """Resposta com o histórico detalhado de mensagens de uma conversa."""

    conversation_id: str
    messages: list[MessageItem]
