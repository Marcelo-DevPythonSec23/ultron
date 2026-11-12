"""TaskDecomposer — decomposição determinística de objetivo em passos (Fase 7).

Recebe um objetivo complexo e devolve uma lista ordenada de passos candidatas,
com alvos sugeridos (agente da Fase 4 ou integração da Fase 5) e dependências.
É uma heurística determinística — não chama modelo de IA, para ser
reproduzível e testável (AGENTS.md §4.7: planejamento separado da execução).
"""

from __future__ import annotations

import re
from typing import Any

from .contracts import StepDependency, WorkflowStep, new_step_id

_KEYWORD_STEPS = [
    # (regex, objetivo, descricao, target_type, target)
    (r"codigo|programar|fun[cç][aã]o|classe|refator|implementar|desenvolver",
     "escrever ou revisar código", "implementar a solução de código solicitada",
     "agent", "developer"),
    (r"pesquisar|buscar|documentar|levantar|investigar",
     "pesquisar informação", "buscar documentação e referências sobre o tema",
     "agent", "research"),
    (r"seguran[cç]a|auditar|permiss|vulnerab",
     "auditar segurança", "revisar contratos, permissões e possíveis segredos",
     "agent", "security"),
    (r"testar|validar|qa|qualidade",
     "executar testes", "rodar suítes de teste e validar resultados",
     "agent", "qa"),
    (r"banco|dados|schema|tabela|sql|persist",
     "inspecionar banco de dados", "verificar esquema e dados (somente leitura)",
     "agent", "database"),
    (r"arquitetura|decis|adr|estrutura|design",
     "revisar arquitetura", "analisar decisões técnicas e impacto arquitetural",
     "agent", "architecture"),
    (r"agente cli|opencode|claude code|mcp|servidor externo",
     "delegar a agente externo", "encaminhar tarefa especializada a ferramenta externa",
     "integration", "opencode"),
]

_FALLBACK_STEP = (
    "executar objetivo",
    "realizar a tarefa solicitada conforme descrito",
    "agent", "developer",
)


def decompose(objective: str, description: str = "") -> list[dict[str, Any]]:
    """Decompõe `objective` em uma lista ordenada de passos candidatos.

    Cada passo: {objective, description, target_type, target}.
    Determinístico: mesmo objetivo => mesmos passos.
    """
    text = f"{objective} {description}".lower()
    steps: list[dict[str, Any]] = []
    seen_targets: set[str] = set()

    for pattern, obj, desc, ttype, target in _KEYWORD_STEPS:
        if re.search(pattern, text):
            if target in seen_targets:
                continue
            seen_targets.add(target)
            steps.append({
                "objective": obj,
                "description": desc,
                "target_type": ttype,
                "target": target,
            })

    if not steps:
        obj, desc, ttype, target = _FALLBACK_STEP
        steps.append({
            "objective": obj,
            "description": desc,
            "target_type": ttype,
            "target": target,
        })

    return steps


def build_steps(objective: str, description: str = "") -> list[WorkflowStep]:
    """Constrói `WorkflowStep`s a partir da decomposição, com dependências lineares.

    Cada passo (exceto o primeiro) depende do sucesso do anterior.
    """
    planned = decompose(objective, description)
    steps: list[WorkflowStep] = []
    previous_id: str | None = None
    for item in planned:
        step = WorkflowStep(
            id=new_step_id(),
            objective=item["objective"],
            description=item["description"],
            target=item["target"],
            target_type=item["target_type"],
        )
        if previous_id is not None:
            step.dependencies.append(
                StepDependency(step_id=previous_id, mode="success")
            )
        steps.append(step)
        previous_id = step.id
    return steps


class TaskDecomposer:
    """Fachada sobre as funções de decomposição (mantida para compatibilidade)."""

    def decompose(self, objective: str, description: str = "") -> list[dict[str, Any]]:
        return decompose(objective, description)

    def build_steps(self, objective: str, description: str = "") -> list[WorkflowStep]:
        return build_steps(objective, description)
