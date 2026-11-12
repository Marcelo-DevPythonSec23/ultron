"""Application Controller da interface desktop (Fase 2.5 — INTERFACE.md).

Usa a interface original do Mark-LVI (`mark_lvi_ui.py`, adaptada de
`Mark-LVI-main/ui.py`) conectada ao `OrchestratorBridge` do ULTRON 2.0.
Não cria um segundo cérebro: consome os serviços existentes através do
`BridgeAdapter`.
"""

from __future__ import annotations

import logging

from .mark_lvi_adapter import MarkLVIAdapter

logger = logging.getLogger("ultron2.interface.application")


class Application:
    """Controlador da aplicação desktop ULTRON 2.0.

    Envolve o `MarkLVIAdapter` que conecta a `JarvisUI` (interface original
    do Mark-LVI) ao `OrchestratorBridge` do ULTRON 2.0.
    """

    def __init__(self) -> None:
        self._adapter = MarkLVIAdapter()
        self._logger = logging.getLogger("ultron2.interface.application.Application")

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
    def adapter(self) -> MarkLVIAdapter:
        return self._adapter

    @property
    def ui(self):
        return self._adapter.ui

    @property
    def bridge(self):
        return self._adapter.bridge


__all__ = ["Application"]
