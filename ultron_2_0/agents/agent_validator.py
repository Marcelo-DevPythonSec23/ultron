"""Validador de resultados de agentes (Fase 4).

Resultados de agentes externos são dados não confiáveis (AGENTS.md §3.3): não
devem ser tratados automaticamente como instruções executáveis nem como fonte
de verdade para a memória canônica. O `AgentValidator` aplica regras
determinísticas de validação antes que o resultado seja aceito pelo
`AgentOrchestrator`.
"""

from __future__ import annotations

import logging
from typing import Any

from .agent_task import AgentResult, AgentTask

logger = logging.getLogger("ultron2.agents.validator")


class AgentValidator:
    """Valida resultados de agentes com regras determinísticas."""

    def __init__(self, *, require_summary: bool = True) -> None:
        self.require_summary = require_summary

    def validate(self, task: AgentTask, result: AgentResult) -> dict[str, Any]:
        """Executa validações e devolve um relatório de validação.

        O relatório contém `valid` (bool), `checks` (lista de dicts com
        nome/pass/mensagem) e `issues` (lista de problemas encontrados).
        """
        checks: list[dict[str, Any]] = []
        issues: list[str] = []

        # 1. Identificação de origem obrigatória.
        origin_ok = bool(result.agent_id and result.agent_type)
        checks.append(
            {
                "name": "origin_identified",
                "pass": origin_ok,
                "message": (
                    "resultado identificado (agente=%s, tipo=%s)"
                    % (result.agent_id, result.agent_type)
                    if origin_ok
                    else "resultado sem identificação de origem"
                ),
            }
        )
        if not origin_ok:
            issues.append("resultado sem identificação de origem")

        # 2. Consistência do task_id.
        task_ok = result.task_id == task.id
        checks.append(
            {
                "name": "task_id_matches",
                "pass": task_ok,
                "message": (
                    "task_id confere com a tarefa"
                    if task_ok
                    else f"task_id {result.task_id!r} difere da tarefa {task.id!r}"
                ),
            }
        )
        if not task_ok:
            issues.append("task_id inconsistente")

        # 3. Resultado não vazio quando bem-sucedido.
        if result.success:
            content_ok = bool(result.content or result.summary)
            checks.append(
                {
                    "name": "non_empty_result",
                    "pass": content_ok,
                    "message": (
                        "resultado possui conteúdo ou sumário"
                        if content_ok
                        else "sucesso sem conteúdo nem sumário"
                    ),
                }
            )
            if not content_ok:
                issues.append("sucesso sem conteúdo")

            # 4. Sumário obrigatório (configurável).
            if self.require_summary:
                summary_ok = bool(result.summary.strip())
                checks.append(
                    {
                        "name": "summary_present",
                        "pass": summary_ok,
                        "message": (
                            "sumário presente"
                            if summary_ok
                            else "sumário ausente em resultado bem-sucedido"
                        ),
                    }
                )
                if not summary_ok:
                    issues.append("sumário ausente")

            # 5. Não modifica arquivos fora do escopo da tarefa.
            out_of_scope = [
                f for f in result.files_modified if f not in task.files_involved
            ]
            scope_ok = not out_of_scope
            checks.append(
                {
                    "name": "files_in_scope",
                    "pass": scope_ok,
                    "message": (
                        "arquivos modificados dentro do escopo"
                        if scope_ok
                        else f"arquivos fora do escopo: {out_of_scope}"
                    ),
                }
            )
            if not scope_ok:
                issues.append("arquivos modificados fora do escopo da tarefa")
        else:
            # Falha registrada: erro deve estar preenchido.
            error_ok = bool(result.error)
            checks.append(
                {
                    "name": "error_recorded",
                    "pass": error_ok,
                    "message": (
                        "erro registrado"
                        if error_ok
                        else "falha sem mensagem de erro"
                    ),
                }
            )
            if not error_ok:
                issues.append("falha sem mensagem de erro")

        valid = not issues
        report = {
            "valid": valid,
            "task_id": task.id,
            "agent_id": result.agent_id,
            "agent_type": result.agent_type,
            "checks": checks,
            "issues": issues,
        }
        if not valid:
            logger.warning(
                "validação falhou para tarefa %s (agente %s): %s",
                task.id,
                result.agent_id,
                "; ".join(issues),
            )
        return report
