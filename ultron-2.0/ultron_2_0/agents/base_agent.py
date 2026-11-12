"""Classe base para agentes especializados do ULTRON (Fase 4).

Um agente especializado possui responsabilidade delimitada, recebe apenas o
contexto necessário para sua tarefa (isolamento) e devolve resultados
estruturados ao `AgentOrchestrator` para avaliação centralizada.

Agentes NÃO modificam diretamente a memória canônica do ULTRON sem
autorização (AGENTS.md §5.2 e §5.5). Resultados de agentes são dados não
confiáveis até passarem pelo `AgentValidator` (AGENTS.md §3.3 e §5.5).

Esta classe base não é um modelo de IA: é um contrato de execução que pode
ser implementado por agentes externos (OpenCode, Claude Code - Fase 5) ou
por adaptadores que delegam para ferramentas existentes do ULTRON.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from .agent_task import AgentCapability, AgentResult, AgentTask, new_agent_id

logger = logging.getLogger("ultron2.agents.base")


class BaseAgent(ABC):
    """Contrato base de um agente especializado.

    Subclasses implementam `capabilities()` e `execute(task)`. O
    `AgentOrchestrator` controla o ciclo de vida; o agente apenas executa a
    tarefa recebida e devolve um `AgentResult`.
    """

    def __init__(self, agent_id: str | None = None, agent_type: str = "base") -> None:
        self.agent_id = agent_id or new_agent_id()
        self.agent_type = agent_type
        self._logger = logging.getLogger(f"ultron2.agents.{agent_type}")

    # -- contrato obrigatório -------------------------------------------------
    @abstractmethod
    def capabilities(self) -> list[AgentCapability]:
        """Lista de capacidades declaradas pelo agente."""

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Executa a tarefa e devolve o resultado estruturado."""

    # -- execução com isolamento e timeout -----------------------------------
    async def run(self, task: AgentTask, *, timeout_seconds: float = 60.0) -> AgentResult:
        """Executa `task` com timeout e tratamento de falhas.

        Falhas nunca comprometem o núcleo: exceções são capturadas e
        convertidas em `AgentResult` com `success=False`.
        """
        started = time.monotonic()
        self._logger.info("agente %s iniciando tarefa %s", self.agent_id, task.id)
        try:
            result = await asyncio.wait_for(
                self.execute(task), timeout=timeout_seconds
            )
            # Garante identificação de origem mesmo se o agente esquecer.
            result.task_id = task.id
            result.agent_id = self.agent_id
            result.agent_type = self.agent_type
            result.created_at = result.created_at or __import__(
                "datetime", fromlist=["datetime"]
            ).datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
            elapsed = time.monotonic() - started
            self._logger.info(
                "agente %s concluiu tarefa %s em %.2fs (sucesso=%s)",
                self.agent_id,
                task.id,
                elapsed,
                result.success,
            )
            return result
        except asyncio.TimeoutError as exc:
            elapsed = time.monotonic() - started
            self._logger.warning(
                "agente %s timeout na tarefa %s após %.2fs", self.agent_id, task.id, elapsed
            )
            return AgentResult(
                task_id=task.id,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                success=False,
                error=f"timeout após {timeout_seconds:g}s",
                summary="execução interrompida por timeout",
            )
        except Exception as exc:  # noqa: BLE001 — falha de agente não derruba o núcleo
            elapsed = time.monotonic() - started
            self._logger.exception(
                "agente %s falhou na tarefa %s após %.2fs: %s",
                self.agent_id,
                task.id,
                elapsed,
                exc,
            )
            return AgentResult(
                task_id=task.id,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                summary="execução interrompida por exceção",
            )

    # -- utilitários ----------------------------------------------------------
    def has_capability(self, name: str) -> bool:
        return any(cap.name == name for cap in self.capabilities())

    def public(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": [cap.public() for cap in self.capabilities()],
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}(id={self.agent_id}, type={self.agent_type})"
