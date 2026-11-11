"""Contratos de dados para integrações externas (Fase 5).

Define `IntegrationTask`, `IntegrationResult`, `IntegrationType` e
`IntegrationState` — a base de comunicação entre o ULTRON e agentes/servidores
externos (OpenCode, Claude Code, servidores MCP).

Nada aqui executa processo externo: são contratos serializáveis que garantem
rastreabilidade, isolamento e identificação de origem (AGENTS.md §4.4, §5.3).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class IntegrationType(str, Enum):
    """Tipo de integração externa."""

    CLI = "cli"      # agente CLI (OpenCode, Claude Code)
    MCP = "mcp"      # servidor MCP (Model Context Protocol)


class IntegrationState(str, Enum):
    """Estados de uma tarefa de integração."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISABLED = "disabled"  # integração desabilitada pelo operador


@dataclass(frozen=True)
class IntegrationCapability:
    """Capacidade declarada de uma integração externa."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 60.0
    requires_approval: bool = False

    def public(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "timeout_seconds": self.timeout_seconds,
            "requires_approval": self.requires_approval,
        }


@dataclass
class IntegrationTask:
    """Uma tarefa delegada a uma integração externa."""

    id: str
    integration_type: IntegrationType
    target: str  # ex: "opencode", "mcp:filesystem"
    prompt: str
    params: dict[str, Any] = field(default_factory=dict)
    state: IntegrationState = IntegrationState.PENDING
    result: "IntegrationResult | None" = None
    error: str | None = None
    attempts: int = 0
    max_attempts: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_seconds: float | None = None

    def touch(self) -> None:
        pass  # mantido para compatibilidade com AgentTask; não usado aqui

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "integration_type": self.integration_type.value,
            "target": self.target,
            "prompt": self.prompt,
            "state": self.state.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "execution_seconds": self.execution_seconds,
            "error": self.error,
            "has_result": self.result is not None,
        }


@dataclass
class IntegrationResult:
    """Resultado estruturado de uma integração externa."""

    task_id: str
    integration_type: IntegrationType
    target: str
    success: bool
    content: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    error: str | None = None
    raw_output: str | None = None  # saída bruta do processo (sem segredos)
    execution_seconds: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "integration_type": self.integration_type.value,
            "target": self.target,
            "success": self.success,
            "content": self.content,
            "summary": self.summary,
            "error": self.error,
            "execution_seconds": self.execution_seconds,
            "created_at": self.created_at.isoformat(),
        }


def new_task_id() -> str:
    return f"integration-{uuid.uuid4().hex[:12]}"
