"""Testes unitários para o gerenciador de contexto (ContextManager)."""

from app.core.context_manager import ContextManager
from app.models.message import ChatMessage, MessageRole


def test_context_manager_empty_messages():
    """Valida comportamento com lista vazia."""
    mgr = ContextManager()
    assert mgr.build_context([]) == []


def test_context_manager_max_messages_limit():
    """Valida que mensagens antigas além do limite de contagem são descartadas."""
    mgr = ContextManager(max_messages=3, max_tokens=10000)
    messages = [
        ChatMessage(role=MessageRole.USER, content=f"msg_{i}")
        for i in range(10)
    ]

    selected = mgr.build_context(messages)
    assert len(selected) == 3
    assert selected[0].content == "msg_7"
    assert selected[1].content == "msg_8"
    assert selected[2].content == "msg_9"


def test_context_manager_token_truncation():
    """Valida que o contexto é truncado quando o limite de tokens é atingido."""
    # Cada mensagem tem 100 caracteres (~25 tokens)
    mgr = ContextManager(max_messages=10, max_tokens=40)
    messages = [
        ChatMessage(role=MessageRole.USER, content="A" * 100),
        ChatMessage(role=MessageRole.ASSISTANT, content="B" * 100),
        ChatMessage(role=MessageRole.USER, content="C" * 100),
    ]

    selected = mgr.build_context(messages)
    # Apenas a mensagem mais recente cabe no limite de ~40 tokens (100 // 4 + 4 = 29 tokens)
    assert len(selected) == 1
    assert selected[0].content == "C" * 100
