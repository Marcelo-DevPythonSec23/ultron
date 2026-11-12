"""RecoveryManager — recuperação de workflows após falhas (Fase 7).

Detecta workflows `FAILED` ou `PAUSED` e oferece operações de recuperação:
replanejar passos falhados (se houver tentativas restantes) ou reiniciar
workflows pausados. Nunca executa sozinho: devolve a lista de ações de
recuperação para que o `WorkflowEngine` as execute
(AGENTS.md §4.7: recuperação após falhas, interrupção humana preservada).
"""

from __future__ import annotations

import logging
from typing import Any

from .contracts import StepState, Workflow, WorkflowState

logger = logging.getLogger("ultron2.autonomy.recovery")


class RecoveryManager:
    """Planeja ações de recuperação para workflows com problemas."""

    def __init__(self, state_tracker=None) -> None:
        self._state_tracker = state_tracker

    def list_workflows_needing_recovery(self, workflows: list[Workflow]) -> list[dict[str, Any]]:
        """Devolve workflows que precisam de recuperação e o porquê."""
        needed: list[dict[str, Any]] = []
        for wf in workflows:
            if wf.state == WorkflowState.FAILED:
                failed_steps = [s for s in wf.steps if s.state == StepState.FAILED]
                retriable = [s for s in failed_steps if s.attempts < s.max_attempts]
                needed.append({
                    "workflow_id": wf.id,
                    "objective": wf.objective,
                    "state": wf.state.value,
                    "reason": "workflow falhou",
                    "failed_steps": len(failed_steps),
                    "retriable_steps": len(retriable),
                    "can_recover": len(retriable) > 0,
                })
            elif wf.state == WorkflowState.PAUSED:
                needed.append({
                    "workflow_id": wf.id,
                    "objective": wf.objective,
                    "state": wf.state.value,
                    "reason": "workflow pausado (interrupção humana)",
                    "failed_steps": 0,
                    "retriable_steps": 0,
                    "can_recover": True,
                })
        return needed

    def plan_recovery(self, workflow: Workflow) -> dict[str, Any]:
        """Devolve um plano de recuperação para `workflow` (não executa)."""
        if workflow.state not in (WorkflowState.FAILED, WorkflowState.PAUSED):
            return {
                "workflow_id": workflow.id,
                "recoverable": False,
                "reason": f"estado {workflow.state.value} não requer recuperação",
                "actions": [],
            }

        actions: list[dict[str, Any]] = []
        if workflow.state == WorkflowState.PAUSED:
            actions.append({
                "type": "resume",
                "description": "retomar execução do workflow pausado",
            })
        else:
            for step in workflow.failed_steps():
                if step.attempts < step.max_attempts:
                    actions.append({
                        "type": "retry_step",
                        "step_id": step.id,
                        "objective": step.objective,
                        "description": f"reexecutar passo {step.id} (tentativa {step.attempts + 1}/{step.max_attempts})",
                    })
                else:
                    actions.append({
                        "type": "skip_step",
                        "step_id": step.id,
                        "objective": step.objective,
                        "description": f"pular passo {step.id} (tentativas esgotadas)",
                    })

        return {
            "workflow_id": workflow.id,
            "objective": workflow.objective,
            "recoverable": len(actions) > 0,
            "actions": actions,
        }

    def recover(self, workflow: Workflow) -> Workflow:
        """Aplica o plano de recuperação ao `workflow` (muta o objeto)."""
        plan = self.plan_recovery(workflow)
        if not plan["recoverable"]:
            return workflow

        StepState = __import__("ultron_2_0.autonomy.contracts", fromlist=["StepState"]).StepState

        for action in plan["actions"]:
            if action["type"] == "resume":
                workflow.state = WorkflowState.RUNNING
                logger.info("workflow %s retomado após pausa", workflow.id)
            elif action["type"] == "retry_step":
                step = workflow.step_by_id(action["step_id"])
                if step is not None:
                    step.state = StepState.PENDING
                    step.error = None
                    logger.info(
                        "workflow %s passo %s replanejado para reexecução",
                        workflow.id, step.id,
                    )
            elif action["type"] == "skip_step":
                step = workflow.step_by_id(action["step_id"])
                if step is not None:
                    step.state = StepState.SKIPPED
                    logger.info(
                        "workflow %s passo %s pulado (tentativas esgotadas)",
                        workflow.id, step.id,
                    )

        if self._state_tracker is not None:
            self._state_tracker.update(workflow)
        return workflow

    def public(self) -> dict[str, Any]:
        return {"recovery_manager": "active"}
