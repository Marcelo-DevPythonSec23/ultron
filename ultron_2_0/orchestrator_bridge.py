from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .tool_registry import ToolRegistry
from .voice_runtime import VoiceRuntime


class OrchestratorBridge:
    """Small adapter that connects the ULTRON core and Mark-LVI runtime."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.ultron_root = self.project_root / "lain"
        self.voice_runtime = VoiceRuntime(self.project_root)
        self.tool_registry = ToolRegistry(self.project_root)
        self.core_ready = self._probe_ultron_core()

    def _probe_ultron_core(self) -> bool:
        if not self.ultron_root.exists():
            return False

        if str(self.ultron_root) not in sys.path:
            sys.path.insert(0, str(self.ultron_root))

        try:
            import app.config  # noqa: F401
            return True
        except Exception:  # pragma: no cover
            return False

    def status(self) -> dict[str, Any]:
        return {
            "core_ready": self.core_ready,
            "ultron_root": str(self.ultron_root),
            "voice_runtime": self.voice_runtime.status(),
            "tools": [tool.name for tool in self.tool_registry.list_contracts()],
        }

    def process_text(self, message: str) -> dict[str, Any]:
        if not self.core_ready:
            return {
                "source": "bridge",
                "content": f"ULTRON core is unavailable; received text from user: {message}",
            }

        return {
            "source": "ultron-core",
            "content": message,
            "tool_ready": bool(self.tool_registry.list_contracts()),
        }

    def process_voice(self, audio_payload: Any, prompt: str = "") -> dict[str, Any]:
        transcript = self.voice_runtime.transcribe(audio_payload, engine="whisper")
        if not transcript:
            transcript = prompt
        return {
            "transcript": transcript,
            "source": "voice-runtime",
            "content": self.process_text(transcript)["content"],
        }
