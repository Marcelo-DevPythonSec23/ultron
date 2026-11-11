"""Registro e descoberta de agentes especializados (Fase 4).

O `AgentRegistry` é o catálogo central de agentes do ULTRON. Ele:

- registra agentes por `agent_type` (ex: "developer", "security");
- permite descoberta por tipo e por capacidade;
- preserva a autoridade central do ULTRON: agentes não se auto-registram
  silenciosamente, são adicionados explicitamente pelo orquestrador;
- não cria histórico conversacional concorrente nem memória independente
  (AGENTS.md §3.2).
"""

from __future__ import annotations

import logging
from typing import Any

from .agent_task import AgentCapability, AgentTask
from .base_agent import BaseAgent

logger = logging.getLogger("ultron2.agents.registry")


class AgentRegistry:
    """Catálogo central de agentes especializados."""

    def __init__(self) -> None:
        # agent_type -> lista de agentes (permite múltiplos do mesmo tipo).
        self._agents: dict[str, list[BaseAgent]] = {}
        # agent_id -> agente para lookup direto.
        self._by_id: dict[str, BaseAgent] = {}

    # -- registro ------------------------------------------------------------
    def register(self, agent: BaseAgent) -> None:
        """Registra um agente no catálogo."""
        self._agents.setdefault(agent.agent_type, []).append(agent)
        self._by_id[agent.agent_id] = agent
        logger.info(
            "Agente '%s' registrado (tipo=%s, id=%s)",
            agent.agent_type,
            agent.agent_id,
            [cap.name for cap in agent.capabilities()],
        )

    def unregister(self, agent_id: str) -> bool:
        """Remove um agente pelo id. Retorna True se removeu."""
        agent = self._by_id.pop(agent_id, None)
        if agent is None:
            return False
        agents = self._agents.get(agent.agent_type, [])
        self._agents[agent.agent_type] = [a for a in agents if a.agent_id != agent_id]
        if not self._agents[agent.agent_type]:
            del self._agents[agent.agent_type]
        logger.info("Agente '%s' removido (tipo=%s)", agent_id, agent.agent_type)
        return True

    # -- descoberta ----------------------------------------------------------
    def get(self, agent_id: str) -> BaseAgent | None:
        return self._by_id.get(agent_id)

    def list_types(self) -> list[str]:
        return list(self._agents.keys())

    def list_agents(self, agent_type: str | None = None) -> list[BaseAgent]:
        if agent_type is None:
            return [a for agents in self._agents.values() for a in agents]
        return list(self._agents.get(agent_type, []))

    def find_by_capability(self, capability_name: str) -> list[BaseAgent]:
        """Devolve agentes que declaram a capacidade `capability_name`."""
        found: list[BaseAgent] = []
        for agents in self._agents.values():
            for agent in agents:
                if agent.has_capability(capability_name):
                    found.append(agent)
        return found

    def select_for_task(self, task: AgentTask) -> BaseAgent | None:
        """Seleciona o melhor agente para uma tarefa.

        Critério: agente do `task.agent_type` com maior número de
        capacidades compatíveis; empate vence o primeiro registrado.
        """
        candidates = self.list_agents(task.agent_type)
        if not candidates:
            return None
        # Seleciona o que declara mais capacidades (heurística simples e
        # determinística; ordem de registro desempata).
        def score(agent: BaseAgent) -> int:
            names = {cap.name for cap in agent.capabilities()}
            return sum(1 for cap in names if cap in {c.name for c in agent.capabilities()})

        # score simples: número de capacidades declaradas (mais = mais especializado).
        candidates_sorted = sorted(
            candidates, key=lambda a: len(a.capabilities()), reverse=True
        )
        return candidates_sorted[0]

    def public(self) -> dict[str, Any]:
        return {
            "types": self.list_types(),
            "agents": {
                agent_type: [agent.public() for agent in agents]
                for agent_type, agents in self._agents.items()
            },
            "total": sum(len(agents) for agents in self._agents.values()),
        }
