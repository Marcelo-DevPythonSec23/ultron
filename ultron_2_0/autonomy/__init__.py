"""Pacote de Autonomia Operacional do ULTRON 2.1 (Fase 7).

Permite que o ULTRON planeje e execute fluxos de trabalho complexos, sem criar
um segundo orquestrador conversacional: apenas decompõe objetivos, delega
passos aos orquestradores existentes (AgentOrchestrator Fase 4,
IntegrationOrchestrator Fase 5) e monitora a execução.

Exporta a API pública:

    Planner, TaskDecomposer, WorkflowEngine, StateTracker, Scheduler,
    RecoveryManager
    Workflow, WorkflowStep, WorkflowState, StepState, StepDependency,
    new_workflow_id, new_step_id
"""

from __future__ import annotations

from .contracts import (
    StepDependency,
    StepState,
    Workflow,
    WorkflowState,
    WorkflowStep,
    new_step_id,
    new_workflow_id,
)
from .planner import Planner
from .recovery_manager import RecoveryManager
from .scheduler import Scheduler
from .state_tracker import StateTracker
from .task_decomposer import TaskDecomposer, build_steps, decompose
from .workflow_engine import WorkflowEngine

__all__ = [
    "Planner",
    "RecoveryManager",
    "Scheduler",
    "StateTracker",
    "StepDependency",
    "StepState",
    "TaskDecomposer",
    "Workflow",
    "WorkflowEngine",
    "WorkflowState",
    "WorkflowStep",
    "build_steps",
    "decompose",
    "new_step_id",
    "new_workflow_id",
]
