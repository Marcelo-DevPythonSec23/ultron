"""Sistema de eventos da interface desktop (INTERFACE.md §17).

Camada de comunicação organizada entre interface e backend. A interface recebe
eventos estruturados do ULTRON e dispara eventos de volta para o backend,
tudo de forma assíncrona, sem bloquear a thread gráfica.

Eventos são uma proposta de contrato mapeada aos serviços reais do ULTRON.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("ultron2.interface.events")


class EventType(str, Enum):
    """Tipos de evento mapeados aos serviços reais do ULTRON."""

    # Ciclo de vida do assistente
    ASSISTANT_INITIALIZED = "assistant.initialized"
    ASSISTANT_STATE_CHANGED = "assistant.state_changed"
    ASSISTANT_LISTENING = "assistant.listening"
    ASSISTANT_PROCESSING = "assistant.processing"
    ASSISTANT_EXECUTING_TOOL = "assistant.executing_tool"
    ASSISTANT_TOOL_COMPLETED = "assistant.tool_completed"
    ASSISTANT_TOOL_FAILED = "assistant.tool_failed"
    ASSISTANT_CONFIRMATION_REQUIRED = "assistant.confirmation_required"
    ASSISTANT_SPEAKING = "assistant.speaking"
    ASSISTANT_INTERRUPTED = "assistant.interrupted"
    ASSISTANT_ERROR = "assistant.error"
    ASSISTANT_OFFLINE = "assistant.offline"

    # Voz
    VOICE_TRANSCRIPTION = "voice.transcription"
    VOICE_PLAYBACK_STARTED = "voice.playback_started"
    VOICE_PLAYBACK_FINISHED = "voice.playback_finished"
    VOICE_DEVICE_CHANGED = "voice.device_changed"

    # Memória
    MEMORY_UPDATED = "memory.updated"

    # Provedores
    PROVIDER_CHANGED = "provider.changed"
    PROVIDER_FAILED = "provider.failed"

    # Tarefas
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Sistema
    SYSTEM_METRICS_UPDATED = "system.metrics_updated"
    SESSION_UPDATED = "session.updated"


@dataclass
class Event:
    """Evento estruturado trocado entre interface e backend."""

    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = "interface"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
        }


class EventSystem:
    """Central de eventos da interface.

    Mantém registradores (callbacks) por tipo de evento e permite emitir
    eventos para o backend ou receber eventos do backend.
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Callable[[Event], None]]] = {}
        self._async_handlers: dict[EventType, list[Callable[[Event], Any]]] = {}
        self._history: list[Event] = []
        self._max_history = 200
        self._logger = logging.getLogger("ultron2.interface.events.EventSystem")

    def on(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Registra um handler síncrono para um tipo de evento."""
        self._handlers.setdefault(event_type, []).append(handler)

    def on_async(self, event_type: EventType, handler: Callable[[Event], Any]) -> None:
        """Registra um handler assíncrono para um tipo de evento."""
        self._async_handlers.setdefault(event_type, []).append(handler)

    def emit(self, event: Event) -> None:
        """Emite um evento para todos os handlers registrados."""
        self._record(event)
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001
                self._logger.exception("handler síncrono falhou para %s: %s", event.type, exc)

        async_handlers = self._async_handlers.get(event.type, [])
        for handler in async_handlers:
            try:
                # Tenta agendar no event loop existente, se houver
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._run_async_handler(handler, event))
                else:
                    # Sem loop rodando: executa de forma síncrona se possível
                    try:
                        handler(event)
                    except Exception:
                        pass
            except RuntimeError:
                # Sem event loop: ignora handlers assíncronos
                pass

    async def _run_async_handler(
        self, handler: Callable[[Event], Any], event: Event
    ) -> None:
        try:
            await handler(event)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("handler assíncrono falhou para %s: %s", event.type, exc)

    def emit_sync(self, event_type: EventType, **payload: Any) -> None:
        """Emite um evento síncrono com payload."""
        self.emit(Event(type=event_type, payload=dict(payload)))

    def _record(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._history[-limit:]]

    def public(self) -> dict[str, Any]:
        return {
            "registered_types": [t.value for t in self._handlers.keys()],
            "history_count": len(self._history),
        }


__all__ = ["EventSystem", "Event", "EventType"]
