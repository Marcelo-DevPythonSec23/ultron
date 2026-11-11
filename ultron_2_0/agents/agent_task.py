"""Contratos de dados do Sistema Multiagente (Fase 4).

Define `AgentTask`, `AgentResult`, `TaskState` e `AgentCapability` — a base
de comunicação estruturada entre o `AgentOrchestrator` (autoridade central de
coordenação) e os agentes especializados.

Nada aqui executa código de agente: são apenas contratos serializáveis que
garantem rastreabilidade, isolamento de contexto e identificação de origem
dos resultados (AGENTS.md §5.1 e §5.4).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskState(str, Enum):
    """Estados permitidos do ciclo de vida de uma tarefa (AGENTS.md §7)."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def transitions(cls, state: "TaskState") -> set["TaskState"]:
        """Transições válidas a partir de um estado."""
        return {
            cls.PENDING: {cls.ASSIGNED, cls.CANCELLED},
            cls.ASSIGNED: {cls.RUNNING, cls.CANCELLED},
            cls.RUNNING: {cls.REVIEW, cls.FAILED, cls.CANCELLED},
            cls.REVIEW: {cls.COMPLETED, cls.FAILED},
            cls.COMPLETED: set(),
            cls.FAILED: {cls.PENDING},  # replanejamento
            cls.CANCELLED: set(),
        }.get(state, set())


@dataclass(frozen=True)
class AgentCapability:
    """Capacidade declarada de um agente (o que ele sabe fazer)."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    requires_authorization: bool = False
    timeout_seconds: float = 60.0

    def public(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "requires_authorization": self.requires_authorization,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class AgentTask:
    """Uma tarefa delegada a um agente especializado.

    Possui identificador, estado, agente responsável, dependências,
    arquivos envolvidos, permissões, resultado e evidências de validação
    (AGENTS.md §7).
    """

    id: str
    objective: str
    description: str
    agent_type: str  # tipo do agente responsável (ex: "developer", "security")
    context: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    files_involved: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    state: TaskState = TaskState.PENDING
    result: "AgentResult | None" = None
    error: str | None = None
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_seconds: float | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def can_transition(self, new_state: TaskState) -> bool:
        return new_state in TaskState.transitions(self.state)

    def to_public_dict(self) -> dict[str, Any]:
        """Versão serializável para diagnóstico (sem credenciais)."""
        return {
            "id": self.id,
            "objective": self.objective,
            "description": self.description,
            "agent_type": self.agent_type,
            "state": self.state.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "execution_seconds": self.execution_seconds,
            "error": self.error,
            "has_result": self.result is not None,
            "dependencies": list(self.dependencies),
            "files_involved": list(self.files_involved),
            "permissions": list(self.permissions),
        }


@dataclass
class AgentResult:
    """Resultado estruturado de um agente, com identificação de origem."""

    task_id: str
    agent_id: str
    agent_type: str
    success: bool
    content: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    files_modified: list[str] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "success": self.success,
            "content": self.content,
            "summary": self.summary,
            "files_modified": list(self.files_modified),
            "validation": self.validation,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }


def new_task_id() -> str:
    return f"task-{uuid.uuid4().hex[:12]}"


def new_agent_id() -> str:
    return f"agent-{uuid.uuid4().hex[:12]}"
