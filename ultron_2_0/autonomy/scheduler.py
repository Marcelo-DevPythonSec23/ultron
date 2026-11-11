"""Scheduler — agendamento de workflows (Fase 7).

Agenda a execução de workflows após um delay ou em um horário absoluto. Não
executa o workflow sozinho: apenas registra a intenção e expõe `is_due()`
para que o `WorkflowEngine` (ou um loop externo) dispare quando o tempo
chegar. Limites de execução são aplicados pelo engine.
"""

from __future__ import annotations

import heapq
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .contracts import Workflow


@dataclass(order=True)
class _ScheduledWorkflow:
    run_at: datetime
    workflow_id: str = field(compare=False)


class Scheduler:
    """Fila de prioridade de workflows agendados por horário de execução."""

    def __init__(self) -> None:
        self._heap: list[_ScheduledWorkflow] = []
        self._lock = threading.Lock()

    def schedule(self, workflow: Workflow, run_at: datetime) -> None:
        """Agenda `workflow` para execução em `run_at`."""
        with self._lock:
            heapq.heappush(self._heap, _ScheduledWorkflow(run_at, workflow.id))
        import logging

        logging.getLogger("ultron2.autonomy.scheduler").info(
            "workflow %s agendado para %s", workflow.id, run_at.isoformat()
        )

    def due(self, now: datetime | None = None) -> list[str]:
        """Devolve IDs de workflows cujo horário de execução já chegou."""
        now = now or datetime.now(timezone.utc)
        due_ids: list[str] = []
        with self._lock:
            while self._heap and self._heap[0].run_at <= now:
                due_ids.append(heapq.heappop(self._heap).workflow_id)
        return due_ids

    def pending(self) -> list[tuple[str, datetime]]:
        """Devolve (workflow_id, run_at) dos agendados pendentes, ordenados."""
        with self._lock:
            return [(item.workflow_id, item.run_at) for item in sorted(self._heap)]

    def cancel(self, workflow_id: str) -> bool:
        with self._lock:
            for i, item in enumerate(self._heap):
                if item.workflow_id == workflow_id:
                    self._heap.pop(i)
                    heapq.heapify(self._heap)
                    return True
        return False

    def public(self) -> dict[str, Any]:
        return {
            "scheduled": len(self._heap),
            "pending": [{"workflow_id": wid, "run_at": run_at.isoformat()} for wid, run_at in self.pending()],
        }
