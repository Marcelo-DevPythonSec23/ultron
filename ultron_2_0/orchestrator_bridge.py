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
    ) -> None:
        self.runtime = UltronCoreRuntime(
            project_root=project_root,
            database_url=database_url,
            default_provider=default_provider,
            enable_tools=enable_tools,
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
        }
