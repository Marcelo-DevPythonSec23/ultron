"""Gerenciador de resultados de agentes (Fase 4).

O `ResultManager` recebe resultados de agentes, os valida via
`AgentValidator`, armazena e expõe ao `AgentOrchestrator` para avaliação
centralizada pelo ULTRON. Resultados nunca são aplicados automaticamente à
memória canônica nem tratados como instruções executáveis (AGENTS.md §3.3).
"""

from __future__ import annotations

import logging
from typing import Any

from .agent_task import AgentResult, AgentTask
from .agent_validator import AgentValidator

logger = logging.getLogger("ultron2.agents.results")


class ResultManager:
    """Recebe, valida e armazena resultados de agentes."""

    def __init__(self, validator: AgentValidator | None = None) -> None:
        self._validator = validator or AgentValidator()
        self._results: dict[str, AgentResult] = {}
        self._validations: dict[str, dict[str, Any]] = {}

    def submit(self, task: AgentTask, result: AgentResult) -> dict[str, Any]:
        """Registra e valida um resultado de agente.

        Devolve o relatório de validação. O resultado só é aceito se
        válido; caso contrário, fica registrado mas marcado como inválido.
        """
        # Garante identificação de origem.
        result.task_id = task.id
        result.agent_id = result.agent_id or "unknown"
        result.agent_type = result.agent_type or task.agent_type

        self._results[task.id] = result
        validation = self._validator.validate(task, result)
        self._validations[task.id] = validation

        if validation["valid"]:
            logger.info(
                "resultado válido para tarefa %s (agente %s)", task.id, result.agent_id
            )
        else:
            logger.warning(
                "resultado inválido para tarefa %s (agente %s): %s",
                task.id,
                result.agent_id,
                "; ".join(validation["issues"]),
            )
        return validation

    def get_result(self, task_id: str) -> AgentResult | None:
        return self._results.get(task_id)

    def get_validation(self, task_id: str) -> dict[str, Any] | None:
        return self._validations.get(task_id)

    def is_valid(self, task_id: str) -> bool:
        validation = self._validations.get(task_id)
        return bool(validation and validation.get("valid"))

    def all_results(self) -> dict[str, AgentResult]:
        return dict(self._results)

    def public(self) -> dict[str, Any]:
        return {
            "total_results": len(self._results),
            "valid_results": sum(1 for v in self._validations.values() if v.get("valid")),
            "results": {
                tid: r.to_public_dict() for tid, r in self._results.items()
            },
        }
