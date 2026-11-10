from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolContract:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required_fields: list[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    requires_confirmation: bool = False
    allowed_modes: list[str] = field(default_factory=lambda: ["text", "voice"])


@dataclass(slots=True)
class ToolResult:
    ok: bool
    tool_name: str
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool_name": self.tool_name,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }
