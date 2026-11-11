"""Application Controller da interface desktop (INTERFACE.md §6).

Ponto de entrada da aplicação desktop ULTRON 2.0. Inicializa o núcleo
(OrchestratorBridge), cria a janela principal e conecta o event system.

Não cria um segundo cérebro: consome os serviços existentes através do
BridgeAdapter.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from PySide6.QtWidgets import QApplication

from .adapters.bridge_adapter import BridgeAdapter
from .events.event_system import EventSystem, EventType
from .themes.ultron_theme import UltronTheme
from .windows.main_window import MainWindow

logger = logging.getLogger("ultron2.interface.application")


class Application:
    """Controlador da aplicação desktop ULTRON 2.0."""

    def __init__(self) -> None:
        self._qt_app: Optional[QApplication] = None
        self._bridge_adapter: Optional[BridgeAdapter] = None
        self._main_window: Optional[MainWindow] = None
        self._event_system = EventSystem()
        self._theme = UltronTheme()
        self._bridge = None
        self._owns_qt_app = False
        self._logger = logging.getLogger("ultron2.interface.application.Application")

    # -- inicialização ------------------------------------------------------
    def initialize(self, bridge=None) -> bool:
        """Inicializa o núcleo e a interface desktop.

        `bridge` pode ser um OrchestratorBridge já iniciado. Se None, cria
        um novo bridge com banco em memória (modo autônomo da interface).
        """
        try:
            # Inicializa QApplication (reusa instância existente se houver)
            existing = QApplication.instance()
            if existing is not None:
                self._qt_app = existing
            else:
                self._qt_app = QApplication(sys.argv)
                self._owns_qt_app = True
            self._qt_app.setApplicationName("ULTRON 2.0")
            self._qt_app.setApplicationVersion("2.1")

            # Obtém ou cria o bridge
            if bridge is None:
                from ultron_2_0.orchestrator_bridge import OrchestratorBridge

                bridge = OrchestratorBridge(
                    database_url="sqlite+aiosqlite:///:memory:",
                    default_provider="mock",
                    enable_tools=True,
                )
                bridge.start()

            self._bridge = bridge
            self._bridge_adapter = BridgeAdapter(bridge)

            # Cria a janela principal
            self._main_window = MainWindow(
                adapter=self._bridge_adapter, theme=self._theme
            )
            self._main_window.show()

            # Conecta o event system à janela
            self._wire_events()

            logger.info("interface desktop inicializada com sucesso")
            return True

        except Exception as exc:  # noqa: BLE001
            logger.exception("falha ao inicializar interface desktop: %s", exc)
            return False

    def _wire_events(self) -> None:
        """Conecta o event system aos componentes da interface."""
        if self._main_window is None or self._bridge_adapter is None:
            return

        # Quando o assistente muda de estado, atualiza o avatar
        def on_state_changed(event) -> None:
            state = event.payload.get("state")
            detail = event.payload.get("detail")
            if state and self._main_window is not None:
                self._main_window.set_assistant_state(state, detail)

        self._event_system.on(
            EventType.ASSISTANT_STATE_CHANGED, on_state_changed
        )

        # Quando uma mensagem é recebida, exibe no chat
        def on_assistant_response(event) -> None:
            content = event.payload.get("content", "")
            provider = event.payload.get("provider")
            model = event.payload.get("model")
            if content and self._main_window is not None:
                self._main_window.append_chat_message(
                    "assistant", content, provider=provider, model=model
                )

        self._event_system.on(
            EventType.ASSISTANT_PROCESSING, lambda e: (
                self._main_window._chat.set_processing(True)
                if self._main_window is not None
                else None
            )
        )

        # Quando uma ferramenta é executada
        def on_tool_completed(event) -> None:
            tool_name = event.payload.get("tool", "desconhecida")
            result = event.payload.get("result", "")
            if self._main_window is not None:
                self._main_window.show_tool_result(tool_name, str(result))

        self._event_system.on(EventType.ASSISTANT_TOOL_COMPLETED, on_tool_completed)

        # Quando ocorre erro
        def on_error(event) -> None:
            message = event.payload.get("message", "erro desconhecido")
            if self._main_window is not None:
                self._main_window.show_chat_error(message)

        self._event_system.on(EventType.ASSISTANT_ERROR, on_error)

    # -- execução -----------------------------------------------------------
    def run(self) -> int:
        """Executa o loop principal da aplicação."""
        if self._qt_app is None:
            raise RuntimeError("aplicação não inicializada — chame initialize()")
        if self._main_window is None:
            raise RuntimeError("janela principal não criada")

        self._logger.info("loop da interface desktop iniciado")
        return self._qt_app.exec()

    def stop(self) -> None:
        """Encerra a aplicação."""
        if self._qt_app is not None:
            self._qt_app.quit()
            if self._owns_qt_app:
                self._qt_app = None
        if self._bridge is not None:
            try:
                self._bridge.stop()
            except Exception:  # noqa: BLE001
                pass

    # -- acessadores --------------------------------------------------------
    @property
    def event_system(self) -> EventSystem:
        return self._event_system

    @property
    def adapter(self) -> Optional[BridgeAdapter]:
        return self._bridge_adapter

    @property
    def main_window(self) -> Optional[MainWindow]:
        return self._main_window

    @property
    def theme(self) -> UltronTheme:
        return self._theme


__all__ = ["Application"]
