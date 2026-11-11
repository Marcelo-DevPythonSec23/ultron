"""Monitor de execução de agentes (Fase 4).

Registra observabilidade de tarefas e agentes: identificador da tarefa, agente
responsável, tempo de execução, estado, falhas, tentativas e resultado da
validação (AGENTS.md §9). Nunca registra credenciais nem dados sensíveis.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .agent_task import AgentResult, AgentTask, TaskState

logger = logging.getLogger("ultron2.agents.monitor")


class ExecutionMonitor:
    """Monitora a execução de tarefas de agentes."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._task_metrics: dict[str, dict[str, Any]] = {}
        self._agent_metrics: dict[str, dict[str, Any]] = {}

    def record_task_created(self, task: AgentTask) -> None:
        self._task_metrics[task.id] = {
            "task_id": task.id,
            "agent_type": task.agent_type,
            "state": task.state.value,
            "attempts": 0,
            "created_at": task.created_at.isoformat(),
            "started_at": None,
            "completed_at": None,
            "execution_seconds": None,
            "success": None,
            "validation": None,
            "error": None,
        }
        self._emit("task_created", task_id=task.id, agent_type=task.agent_type)

    def record_task_started(self, task: AgentTask) -> None:
        m = self._task_metrics.get(task.id)
        if m:
            m["state"] = TaskState.RUNNING.value
            m["started_at"] = task.started_at.isoformat() if task.started_at else None
        self._emit("task_started", task_id=task.id, agent_type=task.agent_type)

    def record_task_completed(
        self, task: AgentTask, result: AgentResult, validation: dict[str, Any]
    ) -> None:
        m = self._task_metrics.get(task.id)
        if m:
            m["state"] = TaskState.COMPLETED.value
            m["completed_at"] = task.completed_at.isoformat() if task.completed_at else None
            m["execution_seconds"] = task.execution_seconds
            m["success"] = result.success
            m["validation"] = validation
            m["error"] = result.error
        self._emit(
            "task_completed",
            task_id=task.id,
            agent_id=result.agent_id,
            agent_type=result.agent_type,
            success=result.success,
            valid=validation.get("valid"),
        )

    def record_task_failed(self, task: AgentTask, error: str) -> None:
        m = self._task_metrics.get(task.id)
        if m:
            m["state"] = TaskState.FAILED.value
            m["error"] = error
            m["attempts"] = task.attempts
        self._emit(
            "task_failed",
            task_id=task.id,
            agent_type=task.agent_type,
            attempts=task.attempts,
            error=error,
        )

    def record_attempt(self, task: AgentTask) -> None:
        m = self._task_metrics.get(task.id)
        if m:
            m["attempts"] = task.attempts

    def public(self) -> dict[str, Any]:
        """Snapshot de observabilidade (sem credenciais)."""
        return {
            "total_tasks": len(self._task_metrics),
            "events_count": len(self._events),
            "tasks": {
                tid: {k: v for k, v in m.items() if k != "validation"}
                for tid, m in self._task_metrics.items()
            },
            "recent_events": self._events[-50:],
        }

    def _emit(self, event: str, **payload: Any) -> None:
        entry = {
            "event": event,
            "at": time.time(),
        }
        entry.update(payload)
        self._events.append(entry)
        # Log resumido (sem conteúdo sensível).
        logger.info(
            "monitor: event=%s task_id=%s agent_type=%s",
            event,
            payload.get("task_id"),
            payload.get("agent_type"),
        )
