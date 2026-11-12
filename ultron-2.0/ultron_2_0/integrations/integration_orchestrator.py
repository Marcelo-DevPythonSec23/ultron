"""Orquestrador de integrações externas (Fase 5).

Coordena tarefas delegadas a integrações externas (OpenCode CLI, servidores
MCP). Cria tarefas, executa via adaptador registrado com timeout e isola
falhas para que não comprometam o núcleo ULTRON.

Não é um segundo orquestrador conversacional: não toca no histórico, memória
canônica nem no `process_text`. Apenas encaminha tarefas especializadas a
agentes/servidores externos e devolve resultados para avaliação do ULTRON.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .contracts import (
    IntegrationResult,
    IntegrationState,
    IntegrationTask,
    IntegrationType,
    new_task_id,
)
from .integration_registry import IntegrationRegistry

logger = logging.getLogger("ultron2.integrations.orchestrator")


class IntegrationOrchestrator:
    """Coordena integrações externas."""

    def __init__(self, registry: IntegrationRegistry | None = None) -> None:
        self._registry = registry or IntegrationRegistry()
        self._tasks: dict[str, IntegrationTask] = {}
        self._results: dict[str, IntegrationResult] = {}
        self._lock = asyncio.Lock()
        self._max_concurrent = 3

    # -- registro de integrações ---------------------------------------------
    def register_integration(self, integration) -> None:
        self._registry.register(integration)

    def unregister_integration(self, target: str) -> bool:
        return self._registry.unregister(target)

    def enable_integration(self, target: str) -> bool:
        return self._registry.enable(target)

    def disable_integration(self, target: str) -> bool:
        return self._registry.disable(target)

    def is_enabled(self, target: str) -> bool:
        return self._registry.is_enabled(target)

    def list_integrations(self) -> dict[str, Any]:
        return self._registry.public()

    # -- criação de tarefas ---------------------------------------------------
    def create_task(
        self,
        *,
        integration_type: IntegrationType,
        target: str,
        prompt: str,
        params: dict[str, Any] | None = None,
        max_attempts: int = 1,
    ) -> IntegrationTask:
        task = IntegrationTask(
            id=new_task_id(),
            integration_type=integration_type,
            target=target,
            prompt=prompt,
            params=dict(params or {}),
            max_attempts=max(1, int(max_attempts)),
        )
        self._tasks[task.id] = task
        logger.info(
            "tarefa de integração %s criada (tipo=%s, alvo=%s)",
            task.id,
            integration_type.value,
            target,
        )
        return task

    def get_task(self, task_id: str) -> IntegrationTask | None:
        return self._tasks.get(task_id)

    def get_result(self, task_id: str) -> IntegrationResult | None:
        return self._results.get(task_id)

    # -- execução -------------------------------------------------------------
    async def run_task(self, task: IntegrationTask) -> IntegrationResult:
        """Executa uma única tarefa de integração com isolamento de falhas."""
        integration = self._registry.get(task.target)
        if integration is None:
            error = f"integração '{task.target}' não registrada"
            logger.error("tarefa %s: %s", task.id, error)
            task.state = IntegrationState.FAILED
            task.error = error
            result = IntegrationResult(
                task_id=task.id,
                integration_type=task.integration_type,
                target=task.target,
                success=False,
                error=error,
                summary="integracao nao registrada",
            )
            self._results[task.id] = result
            return result

        if not integration.is_enabled():
            error = f"integração '{task.target}' desabilitada"
            logger.warning("tarefa %s: %s", task.id, error)
            task.state = IntegrationState.DISABLED
            task.error = error
            result = IntegrationResult(
                task_id=task.id,
                integration_type=task.integration_type,
                target=task.target,
                success=False,
                error=error,
                summary="integracao desabilitada",
            )
            self._results[task.id] = result
            return result

        task.state = IntegrationState.RUNNING
        task.started_at = __import__(
            "datetime", fromlist=["datetime", "timezone"]
        ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
        task.attempts += 1

        try:
            result = await integration.run(task)
            task.execution_seconds = result.execution_seconds
            task.result = result
            self._results[task.id] = result

            if result.success:
                task.state = IntegrationState.COMPLETED
                task.completed_at = __import__(
                    "datetime", fromlist=["datetime", "timezone"]
                ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
                logger.info(
                    "tarefa de integracao %s concluida (alvo=%s, %.2fs)",
                    task.id,
                    task.target,
                    result.execution_seconds or 0,
                )
            else:
                task.state = IntegrationState.FAILED
                task.error = result.error
                logger.warning(
                    "tarefa de integracao %s falhou (alvo=%s): %s",
                    task.id,
                    task.target,
                    result.error,
                )
            return result
        except Exception as exc:  # noqa: BLE001 — falha externa não derruba o núcleo
            task.state = IntegrationState.FAILED
            task.error = f"{type(exc).__name__}: {exc}"
            logger.exception("tarefa de integracao %s excecao: %s", task.id, exc)
            result = IntegrationResult(
                task_id=task.id,
                integration_type=task.integration_type,
                target=task.target,
                success=False,
                error=task.error,
                summary="execucao interrompida por excecao",
            )
            self._results[task.id] = result
            return result

    async def run_ready(self, max_tasks: int | None = None) -> int:
        """Executa tarefas pendentes (até max_tasks ou max_concurrent).

        Como não há fila de dependências entre integrações, executa as
        pendentes em ordem de criação, respeitando concorrência limitada.
        """
        limit = self._max_concurrent if max_tasks is None else max_tasks
        started = 0
        running = 0
        for task in list(self._tasks.values()):
            if started >= limit:
                break
            if task.state != IntegrationState.PENDING:
                continue
            running += 1
            asyncio.create_task(self.run_task(task))
            started += 1
        return started

    # -- observabilidade ------------------------------------------------------
    def status(self) -> dict[str, Any]:
        return {
            "integrations": self._registry.public(),
            "tasks": {
                tid: t.to_public_dict() for tid, t in self._tasks.items()
            },
            "results": {
                tid: r.to_public_dict() for tid, r in self._results.items()
            },
            "total_tasks": len(self._tasks),
            "completed": sum(
                1 for t in self._tasks.values()
                if t.state == IntegrationState.COMPLETED
            ),
            "failed": sum(
                1 for t in self._tasks.values()
                if t.state == IntegrationState.FAILED
            ),
            "pending": sum(
                1 for t in self._tasks.values()
                if t.state == IntegrationState.PENDING
            ),
            "max_concurrent": self._max_concurrent,
        }
