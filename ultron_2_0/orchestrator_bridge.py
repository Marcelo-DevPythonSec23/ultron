"""Adaptador de interface do ULTRON 2.0 (master prompt §5.1).

A camada de interface (CLI de texto hoje, voz na Etapa 3) não decide nada:
ela recebe a entrada do usuário, encaminha ao `UltronCoreRuntime` — que por
sua vez roda o ORQUESTRADOR ORIGINAL do lain, único ciclo conversacional —
e devolve a resposta. Não existe eco, nem fallback por regex, nem um
segundo mecanismo de decisão (master prompt §3.2/§3.3).

Estado de interface mantido aqui (apenas o que é da interface, não do núcleo):
- o `conversation_id` corrente da SESSÃO de interface, para que turnos
  sucessivos caiam na MESMA conversa persistida pelo núcleo (histórico único);
- nada de histórico paralelo: tudo é persistido pelo ChatService do lain.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .core_runtime import UltronCoreRuntime, _mask_db_url

logger = logging.getLogger("ultron2.bridge")


class OrchestratorBridge:
    """Ponta de entrada de interfaces: CLI texto (hoje) e voz (Etapa 3)."""

    def __init__(
        self,
        project_root: str | Path | None = None,
        database_url: str | None = None,
        default_provider: str | None = None,
        enable_tools: bool = True,
        confirmation_handler: Any | None = None,
        authorization: Any | None = None,
        router_config: Any | None = None,
    ) -> None:
        self.runtime = UltronCoreRuntime(
            project_root=project_root,
            database_url=database_url,
            default_provider=default_provider,
            enable_tools=enable_tools,
            confirmation_handler=confirmation_handler,
            authorization=authorization,
            router_config=router_config,
        )
        self._conversation_id: str | None = None

    # -- ciclo de vida --------------------------------------------------------
    def start(self) -> "OrchestratorBridge":
        """Sobe o loop dedicado e o núcleo (idempotente)."""
        self.runtime.start_background()
        return self

    def stop(self) -> None:
        """Encerra o núcleo e o loop dedicado."""
        self.runtime.stop_background()

    def __enter__(self) -> "OrchestratorBridge":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # -- conversa -------------------------------------------------------------
    def process_text(self, message: str, **kwargs: Any):
        """Um turno de conversa pelo orquestrador do lain.

        Mantém o conversation_id da sessão de interface entre chamadas, de
        modo que o histórico acumulado pelo núcleo seja único e contínuo.
        Retorna o `ChatResponse` do lain (conversation_id, message_id,
        content, provider, model, usage, created_at).
        """
        if self.runtime.orchestrator is None:
            raise RuntimeError("núcleo não iniciado — chame start()")
        response = self.runtime.chat_sync(
            message, conversation_id=self._conversation_id, **kwargs
        )
        self._conversation_id = response.conversation_id
        return response

    def new_conversation(self) -> None:
        """Próximo turno inicia uma conversa nova (a anterior permanece no banco)."""
        self._conversation_id = None

    @property
    def conversation_id(self) -> str | None:
        return self._conversation_id

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Histórico persistido da conversa corrente (lido no loop do núcleo).

        A sessão de banco pertence ao event loop dedicado do runtime; ler de
        outro loop (uvicorn, por exemplo) seria inseguro. Por isso a leitura
        passa por `run_coro`, nunca pela sessão diretamente.
        """
        if self.runtime.orchestrator is None or self._conversation_id is None:
            return []
        conversation_id = self._conversation_id

        async def _load():
            return await self.runtime.orchestrator.chat_service.msg_repo.get_messages_by_conversation(
                conversation_id=conversation_id, limit=limit
            )

        rows = self.runtime.run_coro(_load())
        return [self._message_item(row) for row in rows]

    @staticmethod
    def _message_item(row) -> dict[str, Any]:
        tool_calls: list[dict[str, Any]] = []
        if row.raw_metadata:
            try:
                tool_calls = json.loads(row.raw_metadata).get("tool_calls", []) or []
            except (ValueError, TypeError):
                tool_calls = []
        return {
            "id": row.id,
            "role": row.role,
            "content": row.content,
            "provider": row.provider,
            "model": row.model,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "tool_calls": tool_calls,
        }

    # -- autorização (Fase 2) -------------------------------------------------
    def pending_actions(self) -> list[dict[str, Any]]:
        """Pendências de autorização visíveis para a interface (sem tokens)."""
        manager = self.runtime.authorization
        return manager.pending() if manager is not None else []

    def approve_action(self, action_id: str) -> dict[str, Any]:
        manager = self.runtime.authorization
        if manager is None:
            raise RuntimeError("autorização indisponível (ferramentas desligadas)")
        return manager.approve(action_id).public()

    def reject_action(self, action_id: str, reason: str = "rejected by user") -> dict[str, Any]:
        manager = self.runtime.authorization
        if manager is None:
            raise RuntimeError("autorização indisponível (ferramentas desligadas)")
        return manager.reject(action_id, reason=reason).public()

    # -- diagnóstico ----------------------------------------------------------
    def status(self) -> dict[str, Any]:
        """Estado REAL do sistema (nada simulado)."""
        runtime = self.runtime
        if runtime.orchestrator is None:
            return {
                "ready": False,
                "project_root": str(runtime.project_root),
            }
        return {
            "ready": True,
            "default_provider": runtime.registry.default_provider_id,
            "providers": runtime.registry.list_providers(),
            "tools": runtime.gateway.names() if runtime.gateway else [],
            "conversation_id": self._conversation_id,
            "database": _mask_db_url(runtime.settings.DATABASE_URL),
            "memory": str(runtime.memory.path) if runtime.memory else None,
            "pending_approvals": len(self.pending_actions()),
            "router": runtime.router.status() if runtime.router is not None else None,
            "agents": (
                runtime.agent_orchestrator.status()
                if runtime.agent_orchestrator is not None
                else None
            ),
            "integrations": (
                runtime.integration_orchestrator.status()
                if runtime.integration_orchestrator is not None
                else None
            ),
        }
