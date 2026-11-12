"""Registro de atividade do HUD (memória da sessão de interface).

Não é um segundo histórico de conversa: o histórico canônico continua sendo o
do núcleo (SQLite via ChatService do lain). Aqui ficam apenas **eventos
observados pela interface** — turno recebido, resposta devolvida, ferramenta
executada, decisão de autorização e erro — para o painel "Atividade".

Propriedades:

- ring buffer limitado (memória constante, sem arquivo, sem segredo);
- thread-safe (o turno roda em worker thread do `asyncio.to_thread`);
- some ao reiniciar o processo — o que é intencional: não há histórico
  paralelo disputando autoridade com o núcleo.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

MAX_EVENTS = 200


class ActivityLog:
    """Ring buffer de eventos da sessão do HUD."""

    def __init__(self, capacity: int = MAX_EVENTS) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max(1, capacity))
        self._lock = threading.Lock()
        self._seq = 0

    def record(
        self,
        kind: str,
        text: str,
        *,
        detail: Any = None,
        ok: bool | None = None,
    ) -> dict[str, Any]:
        """Registra um evento real. Nunca levanta por conteúdo inválido."""
        safe_text = str(text)[:500]
        with self._lock:
            self._seq += 1
            event = {
                "id": self._seq,
                "kind": str(kind)[:40],
                "text": safe_text,
                "detail": detail,
                "ok": ok,
                "at": round(time.time(), 3),
                "timestamp": time.strftime("%H:%M:%S"),
            }
            self._events.append(event)
            return dict(event)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Eventos mais recentes primeiro (cópia; o chamador não vê o deque)."""
        size = max(1, min(int(limit), MAX_EVENTS))
        with self._lock:
            return [dict(item) for item in list(self._events)[-size:][::-1]]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
