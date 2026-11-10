"""ULTRON 2.0 — camada de integração entre o núcleo ULTRON (lain) e o Mark-LVI.

Terceira estrutura independente (master prompt §3.1): `lain/` e
`Mark-LVI-main/` NUNCA são modificados — apenas importados via sys.path,
resolvido por caminhos absolutos no bootstrap.

Autoridade (master prompt §5.1):

    interface (CLI texto hoje, voz na Etapa 3)
        -> Orchestrator do lain — ÚNICO ciclo de conversa
            -> ProviderRegistry do lain
                -> ToolCallingProvider (protocolo de ferramentas)
                    -> ToolGateway (contrato, validação, timeout)
                        -> actions do Mark-LVI (worker threads)

Importar este pacote já resolve os caminhos (idempotente, CWD-independente),
de modo que os submódulos possam importar `app.*` (lain) e `core`/`providers`
(Mark-LVI) diretamente.
"""

from __future__ import annotations

from . import bootstrap

# Resolve lain/ e Mark-LVI-main/ no sys.path ANTES de importar os submódulos
# que dependem de `app.*` (lain) e `core`/`providers` (Mark-LVI).
bootstrap.ensure_sys_paths()

from .core_runtime import UltronCoreRuntime  # noqa: E402
from .orchestrator_bridge import OrchestratorBridge  # noqa: E402
from .tool_contracts import ToolContract, ToolExecutor, ToolResult  # noqa: E402
from .tool_gateway import ToolGateway  # noqa: E402
from .tool_loop import ToolCallingProvider  # noqa: E402

__all__ = [
    "bootstrap",
    "UltronCoreRuntime",
    "OrchestratorBridge",
    "ToolContract",
    "ToolResult",
    "ToolExecutor",
    "ToolGateway",
    "ToolCallingProvider",
]
