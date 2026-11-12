"""Adaptador da interface original do Mark-LVI (ui.py) para o OrchestratorBridge do ULTRON 2.0.

Conecta a `JarvisUI` (interface desktop original do Mark-LVI, reutilizada de
`Mark-LVI-main/ui.py`) ao núcleo do ULTRON 2.0 sem criar um segundo cérebro:

- Toda mensagem de texto vai para `OrchestratorBridge.process_text()` — o
  mesmo caminho usado pela CLI e pelo HUD web.
- O histórico é persistido pelo `ChatService` do lain (único histórico).
- Não há segundo orquestrador, nem histórico paralelo, nem mecanismo de
  decisão independente.

A interface original do Mark-LVI é reutilizada com fidelidade: canvas
holográfico, avatar, painéis de sistema e tarefas, controles de voz, etc.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from PySide6.QtWidgets import QApplication

from ..orchestrator_bridge import OrchestratorBridge
from .mark_lvi_ui import JarvisUI

logger = logging.getLogger("ultron2.interface.mark_lvi_adapter")


class MarkLVIAdapter:
    """Adapta a `JarvisUI` do Mark-LVI ao `OrchestratorBridge` do ULTRON 2.0.

    A interface original do Mark-LVI é reutilizada com fidelidade visual
    completa. Toda comunicação com o núcleo passa pelo
    `OrchestratorBridge.process_text` — nenhum segundo orquestrador é
    criado.
    """

    def __init__(self) -> None:
        self._qt_app: QApplication | None = None
        self._ui: JarvisUI | None = None
        self._bridge: OrchestratorBridge | None = None
        self._logger = logging.getLogger("ultron2.interface.mark_lvi_adapter")

    # -- inicialização -------------------------------------------------------
    def initialize(self, bridge: OrchestratorBridge | None = None) -> bool:
        """Inicializa a interface desktop e conecta ao bridge do ULTRON.

        Se `bridge` não for fornecido, cria um novo `OrchestratorBridge`
        com banco em memória (modo autônomo da interface).
        """
        try:
            # Qt Application (reusa instância se já existir)
            existing = QApplication.instance()
            if existing is None:
                self._qt_app = QApplication([])
                self._qt_app.setApplicationName("ULTRON 2.0")
                self._qt_app.setApplicationVersion("2.1")
                self._qt_app.setStyle("Fusion")
            else:
                self._qt_app = existing

            # Cria a interface original do Mark-LVI
            self._ui = JarvisUI("face.png")

            # Conecta ao bridge do ULTRON (ou cria um novo)
            if bridge is not None:
                self._bridge = bridge
            else:
                self._bridge = OrchestratorBridge(
                    database_url="sqlite+aiosqlite:///:memory:",
                    default_provider="mock",
                    enable_tools=True,
                )
                self._bridge.start()

            # Conecta o callback de envio de texto ao núcleo ULTRON
            self._ui.on_text_command = self._on_text_command
            self._ui.on_interrupt = self._on_interrupt

            logger.info("Interface desktop do Mark-LVI inicializada com sucesso")
            return True

        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha ao inicializar interface desktop: %s", exc)
            return False

    # -- callbacks da interface ---------------------------------------------
    def _on_text_command(self, text: str) -> None:
        """Chamado quando o usuário envia uma mensagem pela interface."""
        if not text or not text.strip():
            return

        if not self._bridge:
            logger.error("OrchestratorBridge não disponível")
            return

        try:
            response = self._bridge.process_text(text.strip())
            self._display_response(response)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao processar mensagem: %s", exc)
            self._ui.write_log(f"ERR: {exc}")

    def _on_interrupt(self) -> None:
        """Chamado quando o usuário interrompe a fala."""
        logger.info("Interrupção solicitada pela interface")
        # Não há fala ativa para interromper no modo texto;
        # a voz roda em processo separado.

    # -- exibição de resposta -----------------------------------------------
    def _display_response(self, response: Any) -> None:
        """Exibe a resposta do provedor na interface."""
        content = getattr(response, "content", str(response))
        provider = getattr(response, "provider", None)
        model = getattr(response, "model", None)

        # Exibe a resposta do assistente no log do chat
        provider_tag = f" [{provider}]" if provider else ""
        model_tag = f" ({model})" if model else ""
        self._ui.write_log(f"Jarvis{provider_tag}{model_tag}: {content}")

        # Atualiza o estado do avatar para ocioso após a resposta
        self._ui.set_state("IDLE")

    # -- estado da interface ------------------------------------------------
    def set_assistant_state(self, state: str, detail: str | None = None) -> None:
        """Atualiza o estado visual do assistente."""
        if self._ui:
            self._ui.set_state(state)
            if detail:
                self._ui.write_log(f"SYS: {detail}")

    def show_error(self, message: str) -> None:
        """Exibe um erro na interface."""
        if self._ui:
            self._ui.write_log(f"ERR: {message}")

    def show_tool_result(self, tool_name: str, result: str) -> None:
        """Exibe o resultado de uma ferramenta."""
        if self._ui:
            self._ui.write_log(f"[TOOL] {tool_name}: {result}")

    # -- ciclo de vida ------------------------------------------------------
    def run(self) -> int:
        """Entra no event loop do Qt. Bloqueia até a janela ser fechada."""
        if not self._qt_app:
            raise RuntimeError("Interface não inicializada — chame initialize()")
        if self._ui:
            self._ui.root.mainloop()
        return 0

    def stop(self) -> None:
        """Encerra a interface e o bridge."""
        if self._bridge:
            try:
                self._bridge.stop()
            except Exception:  # noqa: BLE001
                pass
        if self._qt_app:
            self._qt_app.quit()

    # -- acessadores --------------------------------------------------------
    @property
    def ui(self) -> JarvisUI | None:
        return self._ui

    @property
    def bridge(self) -> OrchestratorBridge | None:
        return self._bridge


__all__ = ["MarkLVIAdapter"]
