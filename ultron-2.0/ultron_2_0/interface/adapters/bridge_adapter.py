"""Adapter da interface desktop para o OrchestratorBridge (INTERFACE.md §18).

Conecta a interface desktop ao núcleo ULTRON sem criar um segundo cérebro:
- Consome o mesmo OrchestratorBridge (process_text, status, history).
- Não duplica histórico conversacional nem memória.
- Não duplica o processamento de voz.
- Todas as ferramentas passam pelo ToolGateway.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("ultron2.interface.adapters.bridge")


class BridgeAdapter:
    """Adapter entre a interface desktop e o OrchestratorBridge do ULTRON.

    Expõe métodos síncronos e assíncronos para a interface desktop enviar
    mensagens, obter status, histórico e gerenciar aprovações de ferramentas.
    """

    def __init__(self, bridge) -> None:
        self._bridge = bridge
        self._logger = logging.getLogger("ultron2.interface.adapters.bridge.BridgeAdapter")

    # -- conversa -----------------------------------------------------------
    def process_text(self, message: str, **kwargs: Any) -> Any:
        """Envia uma mensagem de texto para o núcleo ULTRON.

        Delegado para OrchestratorBridge.process_text — o mesmo caminho usado
        pela CLI, voz e HUD web. Não cria histórico paralelo.
        """
        try:
            return self._bridge.process_text(message, **kwargs)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("process_text falhou: %s", exc)
            raise

    async def process_text_async(self, message: str, **kwargs: Any) -> Any:
        """Versão assíncrona de process_text (não bloqueia a thread gráfica)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process_text, message, **kwargs)

    # -- status -------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        """Retorna o estado REAL do sistema (nada simulado)."""
        try:
            return self._bridge.status()
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("status falhou: %s", exc)
            return {"ready": False, "error": str(exc)}

    # -- histórico ----------------------------------------------------------
    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retorna o histórico persistido da conversa corrente."""
        try:
            return self._bridge.history(limit=limit)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("history falhou: %s", exc)
            return []

    def new_conversation(self) -> None:
        """Inicia uma nova conversa (a anterior permanece no banco)."""
        self._bridge.new_conversation()

    # -- autorização (Fase 2) ----------------------------------------------
    def pending_actions(self) -> list[dict[str, Any]]:
        """Retorna pendências de autorização visíveis para a interface."""
        try:
            return self._bridge.pending_actions()
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("pending_actions falhou: %s", exc)
            return []

    def approve_action(self, action_id: str) -> dict[str, Any]:
        """Aprova uma ação pendente (token de uso único)."""
        try:
            return self._bridge.approve_action(action_id)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("approve_action falhou: %s", exc)
            raise

    def reject_action(self, action_id: str, reason: str = "rejected by user") -> dict[str, Any]:
        """Rejeita uma ação pendente."""
        try:
            return self._bridge.reject_action(action_id, reason=reason)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("reject_action falhou: %s", exc)
            raise

    # -- ferramentas --------------------------------------------------------
    def tools(self) -> list[dict[str, Any]]:
        """Lista os contratos reais de ferramentas do ToolGateway."""
        try:
            runtime = self._bridge.runtime
            gateway = runtime.gateway if runtime else None
            if gateway is None:
                return []
            contracts = gateway.list_contracts() if hasattr(gateway, "list_contracts") else []
            return [
                {
                    "name": c.name,
                    "description": getattr(c, "description", ""),
                    "parameters": getattr(c, "schema", {}),
                    "required": getattr(c, "required", []),
                    "timeout": getattr(c, "timeout_seconds", None),
                    "confirmation": getattr(c, "requires_confirmation", False),
                    "permissions": getattr(c, "permissions", []),
                }
                for c in contracts
            ]
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("tools falhou: %s", exc)
            return []

    # -- provedores ---------------------------------------------------------
    def providers(self) -> list[str]:
        """Lista os provedores de LLM registrados."""
        try:
            runtime = self._bridge.runtime
            if runtime is None or runtime.registry is None:
                return []
            return runtime.registry.list_providers()
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("providers falhou: %s", exc)
            return []

    def default_provider(self) -> str | None:
        try:
            runtime = self._bridge.runtime
            if runtime is None or runtime.registry is None:
                return None
            return runtime.registry.default_provider_id
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("default_provider falhou: %s", exc)
            return None

    # -- memória ------------------------------------------------------------
    def memory_stats(self) -> dict[str, Any]:
        """Retorna estatísticas observáveis do MemoryEngine (sem conteúdo sensível)."""
        try:
            runtime = self._bridge.runtime
            if runtime is None or runtime.memory_engine is None:
                return {}
            return runtime.memory_engine.stats()
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("memory_stats falhou: %s", exc)
            return {}

    # -- agentes e integrações (Fases 4 e 5) -------------------------------
    def agents_status(self) -> dict[str, Any] | None:
        try:
            runtime = self._bridge.runtime
            if runtime is None or runtime.agent_orchestrator is None:
                return None
            return runtime.agent_orchestrator.status()
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("agents_status falhou: %s", exc)
            return None

    def integrations_status(self) -> dict[str, Any] | None:
        try:
            runtime = self._bridge.runtime
            if runtime is None or runtime.integration_orchestrator is None:
                return None
            return runtime.integration_orchestrator.status()
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("integrations_status falhou: %s", exc)
            return None

    # -- autonomia (Fase 7) -------------------------------------------------
    def autonomy_status(self) -> dict[str, Any] | None:
        try:
            runtime = self._bridge.runtime
            if runtime is None:
                return None
            # WorkflowEngine pode estar no runtime ou no agent_orchestrator
            wf = getattr(runtime, "workflow_engine", None)
            if wf is not None:
                return wf.public()
            return None
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("autonomy_status falhou: %s", exc)
            return None

    # -- voz ----------------------------------------------------------------
    def voice_status(self) -> dict[str, Any]:
        """Estado do sistema de voz (processo separado)."""
        try:
            runtime = self._bridge.runtime
            if runtime is None:
                return {"available": False, "error": "runtime não iniciado"}
            # Voz roda em processo separado; aqui apenas reporta disponibilidade
            return {
                "available": True,
                "separate_process": True,
                "note": "Voz roda em processo separado (python -m ultron_2_0.voice)",
            }
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("voice_status falhou: %s", exc)
            return {"available": False, "error": str(exc)}

    # -- status do bridge -----------------------------------------------------
    def status(self) -> dict[str, Any]:
        """Retorna o status do bridge do ULTRON."""
        if self._bridge:
            return self._bridge.status()
        return {"ready": False}


__all__ = ["BridgeAdapter"]
