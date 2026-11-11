"""Pacote de agentes especializados do ULTRON (Fase 4).

Exporta a API pública do sistema multiagente:

    AgentOrchestrator, AgentRegistry, AgentExecutor (via orchestrator),
    AgentTask, AgentResult, AgentCapability, TaskState
    BaseAgent, TaskQueue, ResultManager, AgentValidator, ExecutionMonitor

O `AgentOrchestrator` é a autoridade central de coordenação de agentes.
Não é um segundo orquestrador conversacional: não toca no histórico, na
memória canônica nem no `process_text`.
"""

from __future__ import annotations

from .agent_orchestrator import AgentOrchestrator
from .agent_registry import AgentRegistry
from .agent_task import AgentCapability, AgentResult, AgentTask, TaskState
from .agent_validator import AgentValidator
from .base_agent import BaseAgent
from .execution_monitor import ExecutionMonitor
from .implementations import (
    ArchitectureAgent,
    DatabaseAgent,
    DeveloperAgent,
    QAAgent,
    ResearchAgent,
    SecurityAgent,
)
from .result_manager import ResultManager
from .task_queue import TaskQueue

__all__ = [
    "AgentCapability",
    "AgentOrchestrator",
    "AgentRegistry",
    "AgentResult",
    "AgentTask",
    "AgentValidator",
    "ArchitectureAgent",
    "BaseAgent",
    "DatabaseAgent",
    "DeveloperAgent",
    "ExecutionMonitor",
    "QAAgent",
    "ResearchAgent",
    "ResultManager",
    "SecurityAgent",
    "TaskQueue",
    "TaskState",
]
