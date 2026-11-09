"""Testes de fluxo e tratamento de erros da CLI interativa."""

from contextlib import asynccontextmanager
from io import StringIO
from types import SimpleNamespace

import pytest
from rich.console import Console

import chat_cli
from app.cli.error_handling import classify_error
from app.cli.terminal import TerminalRenderer
from app.intelligence.providers.mock import MockProvider
from app.intelligence.providers.registry import ProviderRegistry


@pytest.mark.asyncio
async def test_cli_keeps_conversation_after_processing_error(monkeypatch):
    """Valida mensagens consecutivas, retomada após erro e saída da CLI."""
    output = StringIO()
    console = Console(file=output, width=80, force_terminal=False)
    renderer = TerminalRenderer(console)
    inputs = iter(["first", "fail", "second", "sair"])
    monkeypatch.setattr(chat_cli, "TerminalRenderer", lambda: renderer)
    monkeypatch.setattr(TerminalRenderer, "prompt", lambda self: next(inputs))
    monkeypatch.setattr(chat_cli, "init_db", _noop)
    monkeypatch.setattr(
        chat_cli,
        "get_settings",
        lambda: SimpleNamespace(
            DEFAULT_LLM_PROVIDER="mock",
            DEBUG=False,
            LOG_LEVEL="INFO",
            get_gemini_api_key=lambda: None,
        ),
    )
    monkeypatch.setattr(chat_cli, "setup_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        chat_cli,
        "report_error",
        lambda exc, **kwargs: classify_error(exc, provider=kwargs.get("provider")),
    )
    monkeypatch.setattr(chat_cli, "get_session_factory", lambda: _session_context)
    monkeypatch.setattr(chat_cli, "get_prompt_engine", object)
    monkeypatch.setattr(chat_cli, "get_context_manager", lambda settings: object())

    registry = ProviderRegistry(default_provider_id="mock")
    registry.register_provider(MockProvider())
    monkeypatch.setattr(chat_cli, "get_provider_registry", lambda: registry)
    monkeypatch.setattr(chat_cli, "get_conversation_repository", lambda session: object())
    monkeypatch.setattr(chat_cli, "get_message_repository", lambda session: object())
    monkeypatch.setattr(chat_cli, "get_chat_service", lambda conv, msg: object())

    class FakeOrchestrator:
        def __init__(self):
            self.messages: list[tuple[str, str | None]] = []

        async def process_chat(self, request, on_chunk):
            self.messages.append((request.message, request.conversation_id))
            if request.message == "fail":
                raise RuntimeError("provider unavailable")
            on_chunk(f"Response to {request.message}")
            return SimpleNamespace(
                conversation_id=request.conversation_id or "conversation-1",
                content=f"Response to {request.message}",
            )

    orchestrator = FakeOrchestrator()
    monkeypatch.setattr(chat_cli, "get_orchestrator", lambda *args: orchestrator)

    await chat_cli.start_cli()

    assert orchestrator.messages == [
        ("first", None),
        ("fail", "conversation-1"),
        ("second", "conversation-1"),
    ]
    assert "UNKNOWN SYSTEM ERROR" in output.getvalue()
    assert "Response to second" in output.getvalue()


@asynccontextmanager
async def _session_context():
    yield object()


async def _noop():
    return None
