"""Política de seleção de provedor/modelo por tipo de tarefa.

A política não executa nada: recebe o catálogo e a lista de provedores
candidatos e devolve uma ordem determinística. Empates preservam a ordem de
registro no catálogo; `preferred_provider` recebe um bônus pequeno para que o
provedor padrão continue sendo a primeira escolha em tarefas equivalentes.
"""

from __future__ import annotations

from dataclasses import dataclass

from .capabilities import ModelCapabilities, TaskType
from .catalog import ModelCatalog


@dataclass(frozen=True)
class Candidate:
    """Um par provedor+modelo com a pontuação que o justificou."""

    provider_id: str
    model: str
    score: float
    capabilities: ModelCapabilities

    def public(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "model": self.model,
            "score": self.score,
        }


class ModelSelectionPolicy:
    """Ranking determinístico de provedores para uma tarefa."""

    def __init__(self, *, default_bonus: float = 0.10) -> None:
        self.default_bonus = max(0.0, float(default_bonus))

    def rank(
        self,
        catalog: ModelCatalog,
        task: TaskType,
        provider_ids: list[str],
        *,
        exclude: tuple[str, ...] = (),
        preferred: str | None = None,
    ) -> list[Candidate]:
        """Ordena provedores por aderência à tarefa (maior score primeiro)."""
        excluded = set(exclude)
        candidates: list[Candidate] = []
        for provider_id in provider_ids:
            if provider_id in excluded:
                continue
            best = catalog.best(provider_id, task)
            if best is None:
                continue
            score = best.score(task)
            if preferred is not None and provider_id == preferred:
                score += self.default_bonus
            candidates.append(
                Candidate(
                    provider_id=provider_id,
                    model=best.model,
                    score=round(score, 6),
                    capabilities=best,
                )
            )
        # sort estável: empates mantêm a ordem de `provider_ids`.
        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates

    def public(self) -> dict:
        return {"default_bonus": self.default_bonus}
