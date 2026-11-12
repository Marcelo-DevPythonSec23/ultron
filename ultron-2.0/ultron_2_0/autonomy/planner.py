"""Planner — cria um Workflow a partir de um objetivo (Fase 7).

Recebe um objetivo complexo, usa o `TaskDecomposer` para gerar passos e
monta um `Workflow` com limites de segurança. Não executa nada: apenas
planeja (AGENTS.md §4.7: separar planejamento de execução).
"""

from __future__ import annotations

from typing import Any

from .contracts import Workflow, new_workflow_id
from .task_decomposer import build_steps


class Planner:
    """Planeja um workflow a partir de um objetivo."""

    def __init__(
        self,
        *,
        max_steps: int = 50,
        max_execution_seconds: float = 3600.0,
        require_human_approval: bool = False,
    ) -> None:
        self.max_steps = max(1, int(max_steps))
        self.max_execution_seconds = max(1.0, float(max_execution_seconds))
        self.require_human_approval = bool(require_human_approval)

    def plan(
        self,
        objective: str,
        *,
        description: str = "",
        max_steps: int | None = None,
        max_execution_seconds: float | None = None,
        require_human_approval: bool | None = None,
    ) -> Workflow:
        """Cria um `Workflow` com passos decompostos do objetivo."""
        steps = build_steps(objective, description)
        if len(steps) > self.max_steps:
            steps = steps[: self.max_steps]
        return Workflow(
            id=new_workflow_id(),
            objective=objective,
            description=description,
            steps=steps,
            max_steps=max_steps if max_steps is not None else self.max_steps,
            max_execution_seconds=(
                max_execution_seconds if max_execution_seconds is not None
                else self.max_execution_seconds
            ),
            require_human_approval=(
                require_human_approval if require_human_approval is not None
                else self.require_human_approval
            ),
        )

    def public(self) -> dict[str, Any]:
        return {
            "max_steps": self.max_steps,
            "max_execution_seconds": self.max_execution_seconds,
            "require_human_approval": self.require_human_approval,
        }
