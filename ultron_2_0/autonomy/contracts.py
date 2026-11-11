"""Contratos de dados da Autonomia Operacional (Fase 7).

Define `Workflow`, `WorkflowStep`, `WorkflowState` e `StepState` — a base de
planejamento e execução de fluxos de trabalho complexos pelo ULTRON, sem
criar um segundo orquestrador conversacional (AGENTS.md §4.7).

O `WorkflowEngine` recebe objetivos complexos, os decompõe em tarefas via
`TaskDecomposer`/`Planner`, distribui execução ao `AgentOrchestrator` (Fase 4)
ou `IntegrationOrchestrator` (Fase 5), monitora via `ExecutionMonitor` e
gerencia persistência de estado via `StateTracker`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class StepState(str, Enum):
    """Estados de um passo individual de um workflow."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"  # dependência falhou, passo não executado


class WorkflowState(str, Enum):
    """Estados de um workflow completo."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"  # aguardando interrupção/humano


@dataclass(frozen=True)
class StepDependency:
    """Dependência entre passos: este passo requer a conclusão de outro."""

    step_id: str
    # "success" = depende do sucesso; "any" = depende apenas da finalização
    mode: str = "success"


@dataclass
class WorkflowStep:
    """Um passo de um workflow: unidade executável com dependências."""

    id: str
    objective: str
    description: str
    target: str  # agente (ex: "developer") ou integração (ex: "opencode")
    target_type: str  # "agent" | "integration"
    context: dict[str, Any] = field(default_factory=dict)
    dependencies: list[StepDependency] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    max_attempts: int = 3
    attempts: int = 0
    state: StepState = StepState.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_seconds: float | None = None

    def can_transition(self, new_state: StepState) -> bool:
        return new_state in StepState.transitions(self.state)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "description": self.description,
            "target": self.target,
            "target_type": self.target_type,
            "state": self.state.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_seconds": self.execution_seconds,
            "error": self.error,
            "has_result": self.result is not None,
            "dependencies": [d.step_id for d in self.dependencies],
        }


@dataclass
class Workflow:
    """Um fluxo de trabalho: objetivo decomposto em passos executáveis."""

    id: str
    objective: str
    description: str
    steps: list[WorkflowStep] = field(default_factory=list)
    state: WorkflowState = WorkflowState.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    # Limites de segurança (AGENTS.md §4.7)
    max_steps: int = 50
    max_execution_seconds: float = 3600.0
    require_human_approval: bool = False

    def step_by_id(self, step_id: str) -> WorkflowStep | None:
        for s in self.steps:
            if s.id == step_id:
                return s
        return None

    def pending_steps(self) -> list[WorkflowStep]:
        return [s for s in self.steps if s.state == StepState.PENDING]

    def running_steps(self) -> list[WorkflowStep]:
        return [s for s in self.steps if s.state == StepState.RUNNING]

    def completed_steps(self) -> list[WorkflowStep]:
        return [s for s in self.steps if s.state == StepState.COMPLETED]

    def failed_steps(self) -> list[WorkflowStep]:
        return [s for s in self.steps if s.state == StepState.FAILED]

    def is_done(self) -> bool:
        return bool(self.steps) and all(
            s.state in (StepState.COMPLETED, StepState.FAILED, StepState.CANCELLED, StepState.SKIPPED) for s in self.steps
        )

    def all_successful(self) -> bool:
        return bool(self.steps) and all(s.state == StepState.COMPLETED for s in self.steps)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "description": self.description,
            "state": self.state.value,
            "max_steps": self.max_steps,
            "max_execution_seconds": self.max_execution_seconds,
            "require_human_approval": self.require_human_approval,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "steps": [s.to_public_dict() for s in self.steps],
            "step_count": len(self.steps),
            "completed_count": len(self.completed_steps()),
            "failed_count": len(self.failed_steps()),
        }


def new_workflow_id() -> str:
    return f"wf-{uuid.uuid4().hex[:12]}"


def new_step_id() -> str:
    return f"step-{uuid.uuid4().hex[:12]}"


# Adiciona transitions a StepState (depois da definição da classe, para evitar
# referência cíclica no dataclass).
def _register_transitions() -> None:
    StepState.transitions = lambda self: {  # type: ignore[method-assign]
        StepState.PENDING: {StepState.ASSIGNED, StepState.CANCELLED},
        StepState.ASSIGNED: {StepState.RUNNING, StepState.CANCELLED},
        StepState.RUNNING: {StepState.REVIEW, StepState.FAILED, StepState.CANCELLED},
        StepState.REVIEW: {StepState.COMPLETED, StepState.FAILED},
        StepState.COMPLETED: set(),
        StepState.FAILED: {StepState.PENDING},  # replanejamento
        StepState.CANCELLED: set(),
        StepState.SKIPPED: set(),
    }.get(self, set())


_register_transitions()
