"""Adaptação das actions do Mark-LVI para ferramentas do ULTRON 2.0.

Reusa a MAQUINARIA DE DESCOBERTA do próprio Mark-LVI (`core/action_loader.py`)
— nada aqui reimplementa o contrato TOOL, apenas o consome. Os repositórios
originais não são modificados; os módulos são importados via sys.path.

SUBSET CURADO (decisão nº 3 da auditoria, aprovada):

    system_status  — wrapper próprio sobre actions/system_monitor.py
                     (get_system_status(), que não tem TOOL próprio)
    open_app       — actions/open_app.py (TOOL)
    web_search     — actions/web_search.py (TOOL)
    reminder       — actions/reminder.py (TOOL)

As demais 13 tools descobertas ficam DESCONECTADAS por decisão de segurança
(auditoria §15/§16: game_updater desativa o FAILSAFE do pyautogui,
computer_settings usa shell=True, dev_agent/code_helper/file_processor
executam código, browser_control exige playwright ausente). A descoberta
completa roda (é o mesmo scan que o Mark-LVI faz no boot), mas só o subset
curado recebe contrato no gateway.

Notas de ambiente:
- `core/gemini.py` do Mark-LVI lê a chave de config/api_keys.json (inexistente
  aqui) sem levantar erro — o grounding do web_search falha e cai no fallback
  DDG (ddgs instalado no venv do 2.0). Nenhum api_keys.json é criado ou
  editado (regra do Mark-LVI-main/AGENTS.md).
- O executor de system_status devolve o dict de métricas como JSON — fatos
  para o modelo escrever a frase, no espírito de core/outcome.py.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any

from .bootstrap import ensure_sys_paths
from .tool_contracts import ToolContract, ToolResult
from .tool_gateway import ToolGateway

logger = logging.getLogger("ultron2.tools.marklvi")

# Subset aprovado na auditoria (docs/INTEGRATION_AUDIT.md, decisões pendentes).
CURATED_TOOLS = ("system_status", "open_app", "web_search", "reminder")

# Timeouts por ferramenta (segundos) — teto de execução no gateway.
_TOOL_TIMEOUTS = {
    "open_app": 20.0,
    "web_search": 30.0,
    "reminder": 15.0,
    "system_status": 10.0,
}


def _quiet_log(message: str) -> None:
    """Logger silencioso para discover_actions (evita poluir stdout do runtime."""
    logger.debug("%s", message)


def _load_action_module(marklvi_root: Path, module_name: str):
    """Carrega um único módulo de actions/ pelo caminho (padrão do loader)."""
    path = marklvi_root / "actions" / f"{module_name}.py"
    if not path.exists():
        raise ImportError(f"action module not found: {path}")
    spec = importlib.util.spec_from_file_location(f"actions.{module_name}", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"could not build import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def _register_system_status(gateway: ToolGateway, marklvi_root: Path) -> None:
    """Registra system_status (actions/system_monitor.py não tem TOOL)."""
    module = _load_action_module(marklvi_root, "system_monitor")
    get_status = getattr(module, "get_system_status")

    def executor(parameters: dict) -> str:
        metrics: dict = get_status()
        # Fatos como JSON — o modelo escreve a frase no idioma do usuário.
        return json.dumps(metrics, ensure_ascii=False)

    gateway.register(
        ToolContract(
            name="system_status",
            description=(
                "Reads current system metrics: CPU load, RAM usage, CPU "
                "temperature (if available), GPU load (if available), uptime "
                "and process count. Use for any question about how the "
                "computer is doing right now."
            ),
            parameters={"type": "OBJECT", "properties": {}, "required": []},
            required_fields=[],
            timeout_seconds=_TOOL_TIMEOUTS["system_status"],
            requires_confirmation=False,
            permissions=["system:read-metrics"],
            source="Mark-LVI-main/actions/system_monitor.py::get_system_status",
            expected_errors=["psutil failure"],
        ),
        executor,
    )


def build_gateway(project_root: str | Path | None = None) -> ToolGateway:
    """Constrói o gateway com o subset curado de actions do Mark-LVI."""
    _, lain_root, marklvi_root = ensure_sys_paths(project_root)
    gateway = ToolGateway()

    # Descoberta completa com o loader ORIGINAL do Mark-LVI (scan idêntico ao
    # boot do Mark-LVI; erros de import por arquivo são absorvidos e logados).
    from core.action_loader import discover_actions

    discovered = discover_actions(marklvi_root / "actions", logger=_quiet_log)
    discovered_names = sorted(discovered.names())
    logger.info(
        "Descoberta Mark-LVI: %d actions válidas (%s)",
        len(discovered_names),
        ", ".join(discovered_names),
    )

    # system_status é um helper SEM TOOL — wrapper manual.
    _register_system_status(gateway, marklvi_root)

    # Tools com TOOL dict no subset curado.
    for name in CURATED_TOOLS:
        if name == "system_status" or not discovered.has(name):
            continue
        handler = _resolve_handler(discovered, name)
        if handler is None:
            logger.warning("Subset: action '%s' descoberta sem handler — pulando", name)
            continue

        parameters = _declaration_parameters(discovered, name)
        required = parameters.get("required", [])
        description = _declaration_description(discovered, name)

        def make_executor(action_registry, tool_name):
            def executor(parameters: dict) -> str:
                # ctx vazio: sem player/speak/response/session_memory.
                # ActionRegistry.run já captura exceções e devolve str.
                return action_registry.run(tool_name, parameters, ctx={})

            return executor

        gateway.register(
            ToolContract(
                name=name,
                description=description,
                parameters=parameters,
                required_fields=list(required),
                timeout_seconds=_TOOL_TIMEOUTS.get(name, 30.0),
                requires_confirmation=False,
                permissions=_permissions_for(name),
                source=f"Mark-LVI-main/actions/{name}.py",
                expected_errors=_expected_errors_for(name),
            ),
            make_executor(discovered, name),
        )

    not_found = [n for n in CURATED_TOOLS if not gateway.has(n)]
    if not_found:
        logger.warning("Subset curado incompleto — ausentes: %s", ", ".join(not_found))
    return gateway


# -- helpers de introspecção do ActionRegistry ---------------------------------
# O ActionRegistry do Mark-LVI mantém ActionRecords em _actions (o próprio
# main.py dele lê esse atributo para montar get_tool_declarations). O loop de
# execução passa SEMPRE por ActionRegistry.run() — o caminho público — para que
# a introspecção de assinatura e o tratamento de exceção do loader sejam os
# originais do Mark-LVI.


def _records(registry: Any) -> dict:
    actions = getattr(registry, "_actions", None)
    if actions is None:
        raise RuntimeError("ActionRegistry do Mark-LVI não expõe os records (API mudou?)")
    return actions


def _resolve_handler(registry: Any, name: str):
    rec = _records(registry).get(name)
    if rec is None:
        return None
    return rec.handler


def _declaration_parameters(registry: Any, name: str) -> dict:
    rec = _records(registry).get(name)
    return dict(rec.parameters) if rec else {"type": "OBJECT", "properties": {}, "required": []}


def _declaration_description(registry: Any, name: str) -> str:
    rec = _records(registry).get(name)
    return str(rec.description) if rec else name


def _permissions_for(name: str) -> list[str]:
    if name == "open_app":
        return ["process:launch"]
    if name == "web_search":
        return ["network:https"]
    if name == "reminder":
        return ["filesystem:write ~/.jarvis/reminders", "scheduler:systemd-run|at"]
    if name == "system_status":
        return ["system:read-metrics"]
    return []


def _expected_errors_for(name: str) -> list[str]:
    return {
        "open_app": ["app not found", "launch unverified"],
        "web_search": ["all backends failed", "quota exhausted"],
        "reminder": ["scheduler unavailable", "invalid date/time"],
        "system_status": ["psutil failure"],
    }.get(name, [])


# -- leitura direta para interfaces (HUD) --------------------------------------
# O HUD mostra métricas do host no painel esquerdo. Para não duplicar a lógica
# de `actions/system_monitor.py` (psutil, temperatura, GPU), a interface chama
# a MESMA função usada pela tool `system_status`. O módulo é carregado uma vez
# e reutilizado; uma falha do psutil propaga e o endpoint responde com erro
# explícito em vez de inventar números.

_system_status_fn: Any | None = None


def system_snapshot(project_root: str | Path | None = None) -> dict[str, Any]:
    """Snapshot real de CPU/RAM/temp/GPU/uptime (fonte: action do Mark-LVI)."""
    global _system_status_fn
    if _system_status_fn is None:
        _, _, marklvi_root = ensure_sys_paths(project_root)
        module = _load_action_module(marklvi_root, "system_monitor")
        _system_status_fn = getattr(module, "get_system_status")
    return dict(_system_status_fn())
