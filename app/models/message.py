"""Modelos de dados para mensagens e requisições/respostas de LLM."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Papéis de mensagens conversacionais suportados."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Representação unificada de uma mensagem no histórico conversacional."""

    role: MessageRole
    content: str
    name: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMUsage(BaseModel):
    """Métricas de consumo de tokens da chamada de LLM."""

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class LLMRequest(BaseModel):
    """Contrato de solicitação de geração enviado a um LLMProvider."""

    messages: list[ChatMessage]
    system_instruction: str | None = None
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=1)


class LLMResponse(BaseModel):
    """Contrato canônico de resposta de geração retornado por um LLMProvider."""

    content: str
    role: MessageRole = MessageRole.ASSISTANT
    provider: str
    model: str
    usage: LLMUsage = Field(default_factory=LLMUsage)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
