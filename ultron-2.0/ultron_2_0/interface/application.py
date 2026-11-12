"""Application Controller da interface desktop ULTRON 2.0.

Usa a interface original do ULTRON (adaptada para ULTRON) conectada ao
`OrchestratorBridge` do ULTRON 2.0.
Não cria um segundo cérebro: consome os serviços existentes através do
`UltronAdapter`.
"""

from __future__ import annotations

import logging

from .ultron_adapter import UltronAdapter
from .ultron_ui import UltronUI
from .events.event_system import EventSystem, EventType

logger = logging.getLogger("ultron2.interface.application")


class Application:
    """Controlador da aplicação desktop ULTRON 2.0.

    Envolve o `UltronAdapter` que conecta a `UltronUI` (interface original
    do ULTRON, adaptada para ULTRON) ao `OrchestratorBridge` do ULTRON 2.0.
    """

    def __init__(self) -> None:
        self._adapter = UltronAdapter()
        self._logger = logging.getLogger("ultron2.interface.application.Application")
        self._event_system = EventSystem()

    # -- inicialização -------------------------------------------------------
    def initialize(self, bridge=None) -> bool:
        """Inicializa a interface desktop e conecta ao núcleo ULTRON.

        `bridge` pode ser um `OrchestratorBridge` já iniciado. Se None, cria
        um novo com banco em memória (modo autônomo da interface).
        """
        return self._adapter.initialize(bridge)

    # -- execução ------------------------------------------------------------
    def run(self) -> int:
        """Entra no event loop do Qt. Bloqueia até a janela ser fechada."""
        if self._adapter._ui is None:
            raise RuntimeError("Interface não inicializada — chame initialize()")
        self._adapter._ui.root.mainloop()
        return 0

    def stop(self) -> None:
        """Encerra a interface."""
        self._adapter.stop()

    # -- acessadores --------------------------------------------------------
    @property
    def adapter(self) -> UltronAdapter:
        return self._adapter

    @property
    def ui(self) -> UltronUI | None:
        return self._adapter.ui

    @property
    def bridge(self):
        return self._adapter.bridge

    @property
    def main_window(self):
        """Retorna a janela principal (MainWindow da interface)."""
        if self._adapter and self._adapter.ui:
            return self._adapter.ui._win
        return None

    @property
    def event_system(self) -> EventSystem:
        return self._event_system


__all__ = ["Application"]