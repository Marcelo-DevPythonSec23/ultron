"""Pacote de integrações externas do ULTRON 2.1 (Fase 5).

Conecta o ULTRON a agentes/servidores externos (OpenCode CLI, servidores MCP)
por meio de adaptadores independentes, processos isolados com timeout e
controle de permissões por integração.

Exporta a API pública:

    IntegrationOrchestrator, IntegrationRegistry
    ExternalIntegration, OpenCodeAdapter, MCPAdapter
    IntegrationTask, IntegrationResult, IntegrationType, IntegrationState

O `IntegrationOrchestrator` não é um segundo orquestrador conversacional: não
toca no histórico, na memória canônica nem no `process_text`.
"""

from __future__ import annotations

from .cli_adapter import OpenCodeAdapter
from .contracts import (
    IntegrationResult,
    IntegrationState,
    IntegrationTask,
    IntegrationType,
    new_task_id,
)
from .integration_orchestrator import IntegrationOrchestrator
from .integration_registry import IntegrationRegistry
from .mcp_adapter import MCPAdapter
from .base import ExternalIntegration

__all__ = [
    "ExternalIntegration",
    "IntegrationOrchestrator",
    "IntegrationRegistry",
    "IntegrationResult",
    "IntegrationState",
    "IntegrationTask",
    "IntegrationType",
    "MCPAdapter",
    "OpenCodeAdapter",
    "new_task_id",
]
