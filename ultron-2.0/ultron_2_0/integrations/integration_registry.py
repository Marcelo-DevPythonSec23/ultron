"""Registro de integrações externas (Fase 5).

Permite registrar, habilitar e desabilitar individualmente cada integração
(OpenCode CLI, servidores MCP, etc.). O ULTRON mantém autoridade central:
nenhuma integração age sozinha; todas são acionadas por tarefa explícita.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import ExternalIntegration
from .contracts import IntegrationType

logger = logging.getLogger("ultron2.integrations.registry")


class IntegrationRegistry:
    """Catálogo de integrações externas registradas."""

    def __init__(self) -> None:
        # target -> ExternalIntegration
        self._integrations: dict[str, ExternalIntegration] = {}

    def register(self, integration: ExternalIntegration) -> None:
        self._integrations[integration.target] = integration
        logger.info(
            "Integração '%s' registrada (tipo=%s, habilitada=%s)",
            integration.target,
            integration.integration_type.value,
            integration.is_enabled(),
        )

    def unregister(self, target: str) -> bool:
        if target not in self._integrations:
            return False
        del self._integrations[target]
        logger.info("Integração '%s' removida", target)
        return True

    def get(self, target: str) -> ExternalIntegration | None:
        return self._integrations.get(target)

    def list_targets(self) -> list[str]:
        return list(self._integrations.keys())

    def list_by_type(self, integration_type: IntegrationType) -> list[ExternalIntegration]:
        return [
            it for it in self._integrations.values()
            if it.integration_type == integration_type
        ]

    def enable(self, target: str) -> bool:
        it = self.get(target)
        if it is None:
            return False
        it.enable()
        logger.info("Integração '%s' habilitada", target)
        return True

    def disable(self, target: str) -> bool:
        it = self.get(target)
        if it is None:
            return False
        it.disable()
        logger.info("Integração '%s' desabilitada", target)
        return True

    def is_enabled(self, target: str) -> bool:
        it = self.get(target)
        return bool(it and it.is_enabled())

    def public(self) -> dict[str, Any]:
        return {
            "total": len(self._integrations),
            "integrations": {
                target: it.public() for target, it in self._integrations.items()
            },
            "enabled_count": sum(1 for it in self._integrations.values() if it.is_enabled()),
        }
