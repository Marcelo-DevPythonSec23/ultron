"""ULTRON 2.0 integration layer.

This package provides an independent bridge between the original ULTRON project and
Mark-LVI runtime without modifying either original directory.
"""

from .voice_runtime import VoiceRuntime
from .tool_contracts import ToolContract, ToolResult
from .tool_registry import ToolRegistry
from .orchestrator_bridge import OrchestratorBridge

__all__ = [
    "VoiceRuntime",
    "ToolContract",
    "ToolResult",
    "ToolRegistry",
    "OrchestratorBridge",
]
