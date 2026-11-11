"""Pacote de roteamento de modelos do ULTRON 2.1 (Fase 3).

Exporta a API pública usada por `core_runtime`, CLI, HUD e testes:

    ModelRouter, RouterConfig, RoutingProvider
    ModelCatalog, ModelCapabilities, TaskType, infer_task_type
    ModelSelectionPolicy, Candidate
    FallbackManager, RetryManager, RetryPolicy
    MetricsRegistry, ProviderAdapter
"""

from __future__ import annotations

from .adapters import ProviderAdapter
from .capabilities import ModelCapabilities, TaskType, infer_task_type
from .catalog import ModelCatalog, build_catalog
from .fallback import FallbackManager
from .metrics import MetricsRegistry, ProviderMetrics, sanitize_error
from .policy import Candidate, ModelSelectionPolicy
from .retry import RetryManager, RetryPolicy
from .router import AUTO_MODEL, ModelRouter, RouterConfig, RoutingProvider

__all__ = [
    "AUTO_MODEL",
    "Candidate",
    "FallbackManager",
    "MetricsRegistry",
    "ModelCapabilities",
    "ModelCatalog",
    "ModelRouter",
    "ModelSelectionPolicy",
    "ProviderAdapter",
    "ProviderMetrics",
    "RetryManager",
    "RetryPolicy",
    "RouterConfig",
    "RoutingProvider",
    "TaskType",
    "build_catalog",
    "infer_task_type",
    "sanitize_error",
]
