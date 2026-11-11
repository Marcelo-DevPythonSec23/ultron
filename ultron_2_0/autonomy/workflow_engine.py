"""WorkflowEngine — execução de fluxos de trabalho (Fase 7).

Executa um `Workflow` distribuindo seus passos ao `AgentOrchestrator` (Fase 4)
ou `IntegrationOrchestrator` (Fase 5), respeitando dependências, limites de
recursos/tempo, limites de tentativas e recuperação após falhas.

Não é um segundo orquestrador conversacional: apenas delega passos de um
workflow já planejado aos orquestradores existentes e monitora a execução.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .contracts import StepState, Workflow, WorkflowState, WorkflowStep

logger = logging.getLogger("ultron2.autonomy.workflow")


class WorkflowEngine:
    """Executa workflows com controle de dependências, limites e recuperação."""

    def __init__(
        self,
        *,
        agent_orchestrator=None,
        integration_orchestrator=None,
        max_concurrent: int = 3,
    ) -> None:
        self._agent_orchestrator = agent_orchestrator
        self._integration_orchestrator = integration_orchestrator
        self._max_concurrent = max(1, int(max_concurrent))
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    # -- execução de um workflow ---------------------------------------------
    async def run(self, workflow: Workflow) -> Workflow:
        """Executa `workflow` até completar ou falhar.

        Respeita dependências entre passos, `max_steps`, `max_execution_seconds`
        e limites de tentativas de cada passo. Falhas de passo não derivam em
        falha imediata do workflow se houver tentativas restantes.
        """
        if workflow.state not in (WorkflowState.PENDING, WorkflowState.PAUSED):
            raise ValueError(
                f"workflow {workflow.id} não está em estado executável "
                f"({workflow.state.value})"
            )

        workflow.state = WorkflowState.RUNNING
        workflow.started_at = __import__(
            "datetime", fromlist=["datetime", "timezone"]
        ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
        started = time.monotonic()

        try:
            await self._execute_steps(workflow, started)
        finally:
            if workflow.is_done():
                if workflow.all_successful():
                    workflow.state = WorkflowState.COMPLETED
                else:
                    workflow.state = WorkflowState.FAILED
                workflow.completed_at = __import__(
                    "datetime", fromlist=["datetime", "timezone"]
                ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)

        elapsed = time.monotonic() - started
        if elapsed > workflow.max_execution_seconds:
            workflow.state = WorkflowState.FAILED
            workflow.error = "tempo máximo de execução excedido"

        return workflow

    async def _execute_steps(self, workflow: Workflow, started: float) -> None:
        """Executa os passos do workflow respeitando dependências e concorrência."""
        step_by_id = {s.id: s for s in workflow.steps}
        completed: set[str] = set()

        while True:
            # Limite de tempo global.
            if time.monotonic() - started > workflow.max_execution_seconds:
                logger.warning("workflow %s excedeu tempo máximo", workflow.id)
                break

            # Limite de passos.
            if len(workflow.steps) > workflow.max_steps:
                workflow.error = f"número de passos excede max_steps={workflow.max_steps}"
                break

            # Descobre passos cujas dependências estão completas e que ainda não
            # foram executados nem estão rodando.
            ready = [
                s for s in workflow.steps
                if s.state == StepState.PENDING
                and all(d.step_id in completed for d in s.dependencies)
                and s.id not in self._running
            ]

            if not ready:
                # Nada mais a iniciar. Se há passos rodando, aguarda um pouco.
                running = workflow.running_steps()
                if not running:
                    break
                await asyncio.sleep(0.1)
                continue

            # Limite de concorrência.
            available_slots = self._max_concurrent - len(self._running)
            to_start = ready[:available_slots]

            for step in to_start:
                self._running.add(step.id)
                step.state = StepState.RUNNING
                step.started_at = __import__(
                    "datetime", fromlist=["datetime", "timezone"]
                ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
                step.attempts += 1
                asyncio.create_task(self._run_step(workflow, step, step_by_id, completed))

            # Aguarda pelo menos um passo concluir antes de reavaliar.
            await self._wait_any_step(workflow)

    async def _wait_any_step(self, workflow: Workflow) -> None:
        """Aguarda até que pelo menos um passo mude de RUNNING para outro estado."""
        while True:
            await asyncio.sleep(0.1)
            if any(s.state not in (StepState.RUNNING, StepState.ASSIGNED) for s in workflow.steps):
                return
            if time.monotonic() > 1e9:  # salvaguarda (nunca atinge na prática)
                return

    async def _run_step(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        step_by_id: dict[str, WorkflowStep],
        completed: set[str],
    ) -> None:
        """Executa um único passo com isolamento de falhas e replanejamento."""
        try:
            result = await self._dispatch_step(workflow, step)
            step.result = result
            if result.get("success", False):
                step.state = StepState.COMPLETED
                step.completed_at = __import__(
                    "datetime", fromlist=["datetime", "timezone"]
                ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
                completed.add(step.id)
                logger.info(
                    "workflow %s passo %s concluído (alvo=%s)",
                    workflow.id, step.id, step.target,
                )
            else:
                await self._handle_step_failure(workflow, step, step_by_id, completed, result.get("error", "sem detalhes"))
        except Exception as exc:  # noqa: BLE001 — falha de passo não derruba o núcleo
            step.error = f"{type(exc).__name__}: {exc}"
            logger.exception("passo %s exceção: %s", step.id, exc)
            await self._handle_step_failure(
                workflow, step, step_by_id, completed, step.error
            )
        finally:
            self._running.discard(step.id)

    async def _dispatch_step(self, workflow: Workflow, step: WorkflowStep) -> dict[str, Any]:
        """Despacha o passo ao orquestrador adequado (agente ou integração)."""
        from ..agents import AgentOrchestrator  # import local para evitar ciclo
        from ..integrations import IntegrationOrchestrator

        if step.target_type == "integration" and self._integration_orchestrator is not None:
            task = self._integration_orchestrator.create_task(
                integration_type=__import__(
                    "ultron_2_0.integrations.contracts", fromlist=["IntegrationType"]
                ).IntegrationType.CLI,
                target=step.target,
                prompt=f"{step.objective}: {step.description}",
                params=step.context,
                max_attempts=step.max_attempts,
            )
            result = await self._integration_orchestrator.run_task(task)
            return result.to_public_dict() if hasattr(result, "to_public_dict") else {"success": result.success, "error": result.error}

        if step.target_type == "agent" and self._agent_orchestrator is not None:
            task = self._agent_orchestrator.create_task(
                objective=step.objective,
                description=step.description,
                agent_type=step.target,
                context=step.context,
                permissions=step.permissions,
                max_attempts=step.max_attempts,
            )
            await self._agent_orchestrator.run_ready(max_tasks=1)
            # Aguarda a tarefa concluir (polling curto).
            for _ in range(50):
                await asyncio.sleep(0.1)
                t = self._agent_orchestrator.get_task(task.id)
                if t is not None and t.state in (
                    __import__("ultron_2_0.agents.agent_task", fromlist=["TaskState"]).TaskState.COMPLETED,
                    __import__("ultron_2_0.agents.agent_task", fromlist=["TaskState"]).TaskState.FAILED,
                ):
                    break
            r = self._agent_orchestrator.get_result(task.id)
            if r is None:
                return {"success": False, "error": "sem resultado do agente"}
            if hasattr(r, "to_public_dict"):
                return r.to_public_dict()
            return {
                "success": bool(r.get("success", False)),
                "error": r.get("error"),
                "content": r.get("content"),
            }

        return {"success": False, "error": f"nenhum orquestrador disponível para tipo={step.target_type}"}

    async def _handle_step_failure(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        step_by_id: dict[str, WorkflowStep],
        completed: set[str],
        error: str,
    ) -> None:
        """Trata falha de passo: replaneja se houver tentativas, senão marca falhado."""
        step.error = error
        if step.attempts < step.max_attempts:
            step.state = StepState.PENDING
            logger.warning(
                "workflow %s passo %s falhou (tentativa %d/%d), replanejando",
                workflow.id, step.id, step.attempts, step.max_attempts,
            )
        else:
            step.state = StepState.FAILED
            step.completed_at = __import__(
                "datetime", fromlist=["datetime", "timezone"]
            ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
            logger.warning(
                "workflow %s passo %s falhou definitivamente: %s",
                workflow.id, step.id, error,
            )

    # -- observabilidade ------------------------------------------------------
    def public(self) -> dict[str, Any]:
        return {
            "max_concurrent": self._max_concurrent,
            "running": sorted(self._running),
        }
