"""Orquestrador de agentes especializados (Fase 4).

O `AgentOrchestrator` controla o ciclo de vida das tarefas
(`pending -> assigned -> running -> review -> completed/failed/cancelled`),
delega tarefas a agentes especializados via `AgentRegistry`, coordena
execução isolada com `TaskQueue` (evita conflitos de arquivos), valida
resultados via `AgentValidator`/`ResultManager` e monitora tudo via
`ExecutionMonitor`.

É a autoridade central de coordenação de agentes (AGENTS.md §3.2, §5.4,
§7). Não é um segundo orquestrador conversacional: não toca no histórico,
nem na memória canônica, nem no `process_text`. Apenas coordena agentes
especializados sob solicitação do ULTRON.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .agent_task import AgentResult, AgentTask, TaskState, new_task_id
from .agent_validator import AgentValidator
from .agent_registry import AgentRegistry
from .execution_monitor import ExecutionMonitor
from .result_manager import ResultManager
from .task_queue import TaskQueue

logger = logging.getLogger("ultron2.agents.orchestrator")


class AgentOrchestrator:
    """Coordena agentes especializados e delega tarefas."""

    def __init__(
        self,
        *,
        registry: AgentRegistry | None = None,
        queue: TaskQueue | None = None,
        validator: AgentValidator | None = None,
        results: ResultManager | None = None,
        monitor: ExecutionMonitor | None = None,
        max_concurrent: int = 3,
    ) -> None:
        self._registry = registry or AgentRegistry()
        self._queue = queue or TaskQueue()
        self._validator = validator or AgentValidator()
        self._results = results or ResultManager(validator=self._validator)
        self._monitor = monitor or ExecutionMonitor()
        self._max_concurrent = max(1, int(max_concurrent))
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    # -- registro e descoberta ----------------------------------------------
    def register_agent(self, agent) -> None:
        """Registra um agente especializado no catálogo."""
        self._registry.register(agent)

    def unregister_agent(self, agent_id: str) -> bool:
        return self._registry.unregister(agent_id)

    def list_agent_types(self) -> list[str]:
        return self._registry.list_types()

    def list_agents(self, agent_type: str | None = None):
        return self._registry.list_agents(agent_type)

    # -- criação e delegação de tarefas -------------------------------------
    def create_task(
        self,
        *,
        objective: str,
        description: str,
        agent_type: str,
        context: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
        files_involved: list[str] | None = None,
        permissions: list[str] | None = None,
        max_attempts: int = 3,
    ) -> AgentTask:
        """Cria uma nova tarefa e a enfileira para execução."""
        task = AgentTask(
            id=new_task_id(),
            objective=objective,
            description=description,
            agent_type=agent_type,
            context=dict(context or {}),
            dependencies=list(dependencies or []),
            files_involved=list(files_involved or []),
            permissions=list(permissions or []),
            max_attempts=max(1, int(max_attempts)),
        )
        self._queue.enqueue(task)
        self._monitor.record_task_created(task)
        logger.info(
            "tarefa %s criada (agente=%s, objetivo=%s)",
            task.id,
            agent_type,
            objective,
        )
        return task

    def get_task(self, task_id: str) -> AgentTask | None:
        return self._queue.get(task_id)

    def get_result(self, task_id: str) -> AgentResult | None:
        return self._results.get_result(task_id)

    def get_validation(self, task_id: str) -> dict[str, Any] | None:
        return self._results.get_validation(task_id)

    # -- execução -----------------------------------------------------------
    async def run_ready(self, max_tasks: int | None = None) -> int:
        """Executa até `max_tasks` tarefas prontas da fila.

        Retorna o número de tarefas iniciadas nesta chamada. Tarefas são
        executadas com isolamento (uma por agente) e concorrência limitada
        por `max_concurrent`. Conflitos de arquivo são evitados pela
        `TaskQueue`.
        """
        limit = self._max_concurrent if max_tasks is None else min(max_tasks, self._max_concurrent)
        started = 0
        while started < limit and len(self._running) < self._max_concurrent:
            task = await self._queue.next_ready()
            if task is None:
                break
            agent = self._registry.select_for_task(task)
            if agent is None:
                # Nenhum agente disponível para este tipo: mantém pendente e
                # devolve à fila para tentar depois.
                self._queue.mark_done(task.id)
                logger.warning(
                    "tarefa %s sem agente disponível para tipo %s",
                    task.id,
                    task.agent_type,
                )
                continue
            self._running.add(task.id)
            task.attempts += 1
            self._monitor.record_attempt(task)
            asyncio.create_task(self._execute_one(task, agent))
            started += 1
        return started

    async def _execute_one(self, task: AgentTask, agent) -> None:
        """Executa uma única tarefa com ciclo de vida completo."""
        try:
            task.state = TaskState.ASSIGNED
            task.touch()
            self._monitor.record_task_started(task)

            task.state = TaskState.RUNNING
            task.touch()
            self._monitor.record_task_started(task)

            started = time.monotonic()
            result = await agent.run(
                task, timeout_seconds=self._capability_timeout(agent, task)
            )
            elapsed = time.monotonic() - started
            task.execution_seconds = round(elapsed, 4)

            # Validação do resultado (dados não confiáveis até validar).
            task.state = TaskState.REVIEW
            task.touch()
            validation = self._results.submit(task, result)
            task.result = result

            if validation["valid"] and result.success:
                task.state = TaskState.COMPLETED
                task.completed_at = __import__(
                    "datetime", fromlist=["datetime", "timezone"]
                ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
                task.touch()
                self._monitor.record_task_completed(task, result, validation)
                logger.info(
                    "tarefa %s concluída com sucesso (agente %s, %.2fs)",
                    task.id,
                    agent.agent_id,
                    elapsed,
                )
            else:
                task.state = TaskState.FAILED
                task.error = (
                    result.error
                    or "; ".join(validation.get("issues", []))
                    or "resultado inválido"
                )
                task.touch()
                self._monitor.record_task_failed(task, task.error)
                logger.warning(
                    "tarefa %s falhou (agente %s): %s",
                    task.id,
                    agent.agent_id,
                    task.error,
                )
                # Replanejamento: se ainda há tentativas, volta a pending.
                if task.attempts < task.max_attempts:
                    task.state = TaskState.PENDING
                    task.touch()
                    self._queue.enqueue(task)
                    self._monitor.record_task_created(task)
                    logger.info(
                        "tarefa %s replanejada (tentativa %d/%d)",
                        task.id,
                        task.attempts,
                        task.max_attempts,
                    )
        except Exception as exc:  # noqa: BLE001 — falha de agente não derruba o núcleo
            task.state = TaskState.FAILED
            task.error = f"{type(exc).__name__}: {exc}"
            task.touch()
            self._monitor.record_task_failed(task, task.error)
            logger.exception("tarefa %s exceção não tratada: %s", task.id, exc)
        finally:
            self._running.discard(task.id)
            self._queue.mark_done(task.id)

    def _capability_timeout(self, agent, task: AgentTask) -> float:
        for cap in agent.capabilities():
            if cap.name == task.objective:
                return cap.timeout_seconds
        return 60.0

    # -- observabilidade ----------------------------------------------------
    def status(self) -> dict[str, Any]:
        """Snapshot real do estado do multiagente (sem credenciais)."""
        return {
            "agents": self._registry.public(),
            "queue": self._queue.public(),
            "results": self._results.public(),
            "monitor": self._monitor.public(),
            "running": sorted(self._running),
            "max_concurrent": self._max_concurrent,
        }
