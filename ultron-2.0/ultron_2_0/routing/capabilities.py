"""Capacidades de modelos/provedores e inferência determinística de tarefa.

A Fase 3 separa duas coisas que o núcleo do lain não precisa conhecer:

* **o que cada modelo sabe fazer** (`ModelCapabilities`) — janela de contexto,
  suporte a ferramentas/streaming, qualidade estimada, latência e custo;
* **que tipo de tarefa o turno pede** (`infer_task_type`) — heurística
  determinística, sem chamada de modelo, para que a seleção seja reproduzível
  e testável.

Nada aqui decide execução: são dados de entrada para `policy.py`. As
estimativas são metadados declarados pelo ULTRON (não medições inventadas);
o que não é conhecido fica `None` e é tratado como neutro no ranking.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum


class TaskType(str, Enum):
    """Tipos de tarefa reconhecidos pela política de seleção."""

    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    LONG_CONTEXT = "long_context"
    CHEAP = "cheap"


# -- perfis conhecidos -------------------------------------------------------
# Valores conservadores e documentados em docs/ARCHITECTURE.md. `quality` é uma
# estimativa relativa (0..1) usada SÓ para ordenar candidatos; não é uma medida
# de benchmark. Custos desconhecidos ficam None (neutros), nunca 0 "de graça".
KNOWN_PROFILES: dict[str, dict] = {
    "mock": {
        "quality": 0.25,
        "context_window": 8_192,
        "tags": ("offline", "test"),
        "latency": "fast",
    },
    "gemini": {
        "quality": 0.85,
        "context_window": 1_000_000,
        "tags": ("reasoning", "code", "vision"),
        "latency": "standard",
    },
    "nvidia": {
        "quality": 0.90,
        "context_window": 128_000,
        "tags": ("reasoning", "code", "vision", "nvidia", "nim"),
        "latency": "standard",
    },
}

_DEFAULT_PROFILE: dict = {
    "quality": 0.5,
    "context_window": 8_192,
    "tags": (),
    "latency": "standard",
}

_LATENCY_SCORE = {"fast": 1.0, "standard": 0.5, "slow": 0.0}


def profile_for(provider_id: str) -> dict:
    """Perfil de capacidades do provedor (cópia defensiva)."""
    base = dict(_DEFAULT_PROFILE)
    base.update(KNOWN_PROFILES.get(provider_id, {}))
    return base


@dataclass(frozen=True)
class ModelCapabilities:
    """Metadados de um modelo concreto oferecido por um provedor."""

    provider_id: str
    model: str
    context_window: int = 8_192
    supports_tools: bool = True
    supports_streaming: bool = True
    quality: float = 0.5
    latency: str = "standard"
    cost_input_per_million: float | None = None
    cost_output_per_million: float | None = None
    tags: tuple[str, ...] = ()

    @classmethod
    def for_provider(
        cls,
        provider_id: str,
        model: str,
        *,
        context_window: int | None = None,
        supports_tools: bool = True,
        supports_streaming: bool = True,
    ) -> "ModelCapabilities":
        """Constrói capacidades a partir do perfil conhecido do provedor."""
        profile = profile_for(provider_id)
        return cls(
            provider_id=provider_id,
            model=model,
            context_window=(
                int(context_window)
                if context_window is not None
                else int(profile["context_window"])
            ),
            supports_tools=supports_tools,
            supports_streaming=supports_streaming,
            quality=float(profile["quality"]),
            latency=str(profile["latency"]),
            tags=tuple(profile["tags"]),
        )

    def score(self, task: TaskType) -> float:
        """Aderência do modelo ao tipo de tarefa (maior é melhor).

        Fórmula determinística e documentada; empates são resolvidos pela
        ordem de registro no catálogo (sort estável).
        """
        quality = _clamp(self.quality)
        if task is TaskType.CHAT:
            return round(quality, 6)
        if task is TaskType.CODE:
            bonus = 0.25 if "code" in self.tags else 0.0
            if "offline" in self.tags:
                bonus -= 0.15
            return round(quality * 0.75 + bonus, 6)
        if task is TaskType.REASONING:
            bonus = 0.25 if "reasoning" in self.tags else 0.0
            return round(quality * 0.75 + bonus, 6)
        if task is TaskType.LONG_CONTEXT:
            context = max(1, int(self.context_window))
            # 1k tokens -> 0, 1M tokens -> 1 (escala logarítmica).
            context_score = min(1.0, math.log10(context / 1_000) / 3)
            return round(quality * 0.5 + context_score * 0.5, 6)
        if task is TaskType.CHEAP:
            speed = _LATENCY_SCORE.get(self.latency, 0.5)
            if self.cost_output_per_million is None:
                cost = 0.5  # custo desconhecido não penaliza nem premia
            else:
                cost = 1.0 / (1.0 + max(0.0, float(self.cost_output_per_million)))
            return round(speed * 0.5 + cost * 0.4 + quality * 0.1, 6)
        raise ValueError(f"tipo de tarefa desconhecido: {task!r}")

    def public(self) -> dict:
        """Versão serializável (sem qualquer credencial — não há nenhuma)."""
        return {
            "provider_id": self.provider_id,
            "model": self.model,
            "context_window": self.context_window,
            "supports_tools": self.supports_tools,
            "supports_streaming": self.supports_streaming,
            "quality": self.quality,
            "latency": self.latency,
            "cost_input_per_million": self.cost_input_per_million,
            "cost_output_per_million": self.cost_output_per_million,
            "tags": list(self.tags),
        }


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


# -- inferência de tarefa ----------------------------------------------------
_CODE = re.compile(
    r"\b(c[oó]digo|code|coding|programa|programar|fun[cç][aã]o|function|classe|"
    r"class|refator\w*|refactor\w*|bug|debug|traceback|stack ?trace|python|"
    r"javascript|typescript|sql|api|endpoint|algoritmo|algorithm|"
    r"teste unit[aá]rio|unit test|implemente|implement)\b",
    re.IGNORECASE,
)
_REASONING = re.compile(
    r"\b(analise|analisar|compare|comparar|explique|explicar|por que|why|"
    r"prove|provar|planeje|planejar|plano|arquitetura|architecture|"
    r"estrat[eé]gia|trade-?off|avalie|avaliar|raciocin\w*|reason\w*|"
    r"dedu[cz]\w*|hip[oó]tese)\b",
    re.IGNORECASE,
)
_CHEAP = re.compile(
    r"\b(resuma|resumir|resumo|traduza|traduzir|liste|listar|formate|formatar|"
    r"classifique|classificar|converta|converter|extraia|extrair)\b",
    re.IGNORECASE,
)
_LONG_PHRASE = re.compile(
    r"\b(texto abaixo|seguinte texto|documento abaixo|log abaixo|"
    r"conte[uú]do abaixo)\b",
    re.IGNORECASE,
)

LONG_CONTEXT_CHARS = 4_000


def infer_task_type(
    text: str,
    *,
    task: TaskType | str | None = None,
    long_context_chars: int = LONG_CONTEXT_CHARS,
) -> TaskType:
    """Classifica o turno em um `TaskType` sem chamar nenhum modelo.

    Ordem de precedência (documentada): contexto longo (tamanho/frase) →
    código → raciocínio → tarefa barata → conversa. `task` explícito sempre
    vence (usado por agentes/testes via API de seleção).
    """
    if task is not None:
        return task if isinstance(task, TaskType) else TaskType(str(task))
    content = (text or "").strip()
    if len(content) >= max(1, int(long_context_chars)) or _LONG_PHRASE.search(content):
        return TaskType.LONG_CONTEXT
    if _CODE.search(content):
        return TaskType.CODE
    if _REASONING.search(content):
        return TaskType.REASONING
    if _CHEAP.search(content):
        return TaskType.CHEAP
    return TaskType.CHAT
