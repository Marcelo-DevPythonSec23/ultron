from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from .tool_contracts import ToolContract, ToolResult


class ToolRegistry:
    """Registry for Mark-LVI actions adapted as ULTRON tools."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.mark_lvi_root = self.project_root / "Mark-LVI-main"
        self._tools: dict[str, ToolContract] = {}
        self._executors: dict[str, Any] = {}
        self._load_default_tools()

    def _load_default_tools(self) -> None:
        self._register_action_tool(
            module_name="open_app",
            tool_name="open_app",
            description="Open an application on this system.",
            required_fields=["app_name"],
            timeout_seconds=16.0,
            requires_confirmation=False,
            parameters={
                "type": "OBJECT",
                "properties": {"app_name": {"type": "STRING", "description": "Application name to open"}},
                "required": ["app_name"],
            },
        )

        self._register_action_tool(
            module_name="system_monitor",
            tool_name="system_status",
            description="Read current CPU, RAM, temp and uptime status.",
            required_fields=[],
            timeout_seconds=10.0,
            parameters={
                "type": "OBJECT",
                "properties": {},
                "required": [],
            },
        )

        self._register_action_tool(
            module_name="web_search",
            tool_name="web_search",
            description="Search the web with support for search, news and research modes.",
            required_fields=["query"],
            timeout_seconds=25.0,
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Search text or question"},
                    "mode": {"type": "STRING", "description": "search | news | research | price | compare"},
                    "items": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "aspect": {"type": "STRING", "description": "Comparison aspect"},
                },
                "required": ["query"],
            },
        )

    def _register_action_tool(
        self,
        module_name: str,
        tool_name: str,
        description: str,
        required_fields: list[str],
        timeout_seconds: float,
        parameters: dict[str, Any],
        requires_confirmation: bool = False,
    ) -> None:
        module_path = self.mark_lvi_root / "actions" / f"{module_name}.py"
        if not module_path.exists():
            return

        spec = importlib.util.spec_from_file_location(f"ultron_bridge_action_{module_name}", module_path)
        if spec is None or spec.loader is None:
            return

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            return

        target = getattr(module, module_name, None)
        if target is None:
            target = getattr(module, module_name.replace("_", ""), None)
        if target is None and hasattr(module, "web_search"):
            target = module.web_search
        if target is None and hasattr(module, "get_system_status"):
            target = module.get_system_status
        if target is None and hasattr(module, "open_app"):
            target = module.open_app
        if target is None:
            return

        contract = ToolContract(
            name=tool_name,
            description=description,
            parameters=parameters,
            required_fields=required_fields,
            timeout_seconds=timeout_seconds,
            requires_confirmation=requires_confirmation,
            allowed_modes=["text", "voice"],
        )
        self._tools[tool_name] = contract
        self._executors[tool_name] = target

    def register(self, tool_name: str, contract: ToolContract, executor: Any) -> None:
        self._tools[tool_name] = contract
        self._executors[tool_name] = executor

    def list_contracts(self) -> list[ToolContract]:
        return list(self._tools.values())

    def execute(self, tool_name: str, **kwargs: Any) -> ToolResult:
        if tool_name not in self._executors:
            return ToolResult(ok=False, tool_name=tool_name, error=f"Unknown tool: {tool_name}")

        executor = self._executors[tool_name]
        try:
            result = executor(parameters=kwargs) if tool_name in {"open_app", "web_search"} else executor()
            return ToolResult(ok=True, tool_name=tool_name, result=result)
        except Exception as exc:  # pragma: no cover
            return ToolResult(ok=False, tool_name=tool_name, error=str(exc))
