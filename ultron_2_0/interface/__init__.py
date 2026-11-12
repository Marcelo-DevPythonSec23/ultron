"""Pacote de interface desktop do ULTRON 2.0.

Implementa a interface desktop especificada em `docs/INTERFACE.md`, reutilizando
o Mark LVI como referência visual e funcional, integrado ao núcleo ULTRON
(OrchestratorBridge, VoicePipeline, MemoryEngine, ProviderRegistry, ToolGateway).

A interface NÃO cria um segundo cérebro: consome os serviços existentes e
apresenta seus estados e resultados reais.
"""

from __future__ import annotations

from .application import Application
from .ultron_adapter import UltronAdapter
from .ultron_ui import UltronUI

__all__ = ["Application", "UltronAdapter", "UltronUI"]