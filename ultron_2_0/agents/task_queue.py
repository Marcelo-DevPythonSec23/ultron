"""Fila de tarefas concorrentes com controle de conflitos de arquivos (Fase 4).

A `TaskQueue` gerencia a ordem de execução de tarefas e evita que duas
tarefas concorrentes modifiquem os mesmos arquivos simultaneamente
(AGENTS.md §5.4). Tarefas com dependências só são liberadas após suas
dependências estarem `completed`.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Any

from .agent_task import AgentTask, TaskState

logger = logging.getLogger("ultron2.agents.queue")


class TaskQueue:
    """Fila ordenada de tarefas com controle de concorrência por arquivo."""

    def __init__(self) -> None:
        self._queue: deque[AgentTask] = deque()
        self._tasks: dict[str, AgentTask] = {}
        self._in_progress: set[str] = set()
        self._lock = asyncio.Lock()

    # -- manipulação ---------------------------------------------------------
    def enqueue(self, task: AgentTask) -> None:
        """Adiciona uma tarefa à fila."""
        self._tasks[task.id] = task
        self._queue.append(task)
        logger.info("Tarefa %s enfileirada (estado=%s)", task.id, task.state.value)

    def get(self, task_id: str) -> AgentTask | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> list[AgentTask]:
        return list(self._tasks.values())

    def _files_busy(self, task: AgentTask) -> set[str]:
        """Arquivos de `task` que já estão sendo tocados por tarefas em andamento."""
        busy: set[str] = set()
        wanted = set(task.files_involved)
        for tid in self._in_progress:
            other = self._tasks.get(tid)
            if other is None:
                continue
            busy |= wanted & set(other.files_involved)
        return busy

    async def next_ready(self) -> AgentTask | None:
        """Devolve a próxima tarefa pronta para execução ou None.

        Uma tarefa está pronta quando:
        - estado é PENDING;
        - todas as dependências estão COMPLETED;
        - nenhum de seus arquivos está em uso por outra tarefa em andamento.
        """
        async with self._lock:
            ready: list[AgentTask] = []
            remaining: deque[AgentTask] = deque()
            while self._queue:
                task = self._queue.popleft()
                if task.state != TaskState.PENDING:
                    continue
                deps_ok = all(
                    self._tasks.get(d) is not None
                    and self._tasks[d].state == TaskState.COMPLETED
                    for d in task.dependencies
                )
                if not deps_ok:
                    remaining.append(task)
                    continue
                if self._files_busy(task):
                    remaining.append(task)
                    continue
                ready.append(task)
            self._queue = remaining
            if not ready:
                return None
            task = ready[0]
            self._in_progress.add(task.id)
            # Devolve as demais prontas de volta à fila (manter ordem).
            for extra in ready[1:]:
                self._queue.appendleft(extra)
            return task

    def mark_running(self, task_id: str) -> None:
        self._tasks[task_id].state = TaskState.RUNNING
        self._tasks[task_id].started_at = __import__(
            "datetime", fromlist=["datetime", "timezone"]
        ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
        self._tasks[task_id].touch()

    def mark_done(self, task_id: str) -> None:
        self._in_progress.discard(task_id)

    def public(self) -> dict[str, Any]:
        return {
            "queued": len(self._queue),
            "in_progress": len(self._in_progress),
            "total": len(self._tasks),
            "in_progress_ids": sorted(self._in_progress),
            "tasks": [
                {
                    "id": t.id,
                    "state": t.state.value,
                    "agent_type": t.agent_type,
                    "files_involved": list(t.files_involved),
                }
                for t in self.all_tasks()
            ],
        }
