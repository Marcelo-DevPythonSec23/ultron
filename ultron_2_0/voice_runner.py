from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:  # pragma: no cover - optional dependency
    import sounddevice as sd
except Exception:  # pragma: no cover
    sd = None

from .orchestrator_bridge import OrchestratorBridge


class VoiceRunner:
    """Concrete voice-first runner for the ULTRON 2.0 integration layer.

    This runner keeps the conversation authority in the ULTRON core and reuses the
    Mark-LVI runtime only as an operational backend. If the original ULTRON core is
    unavailable in the current environment, the runner falls back to local tool
    execution and text-guided responses so the voice pipeline still works.
    """

    def __init__(self, project_root: str | Path | None = None, enable_audio: bool = True) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.enable_audio = enable_audio
        self.bridge = OrchestratorBridge(self.project_root)

    def run_text(self, text: str) -> dict[str, Any]:
        message = (text or "").strip()
        if not message:
            return {"status": "empty", "response": "No message received."}

        if self.bridge.core_ready:
            return {
                "status": "ok",
                "source": "ultron-core",
                "response": self.bridge.process_text(message)["content"],
            }

        result = self._fallback_command(message)
        return {
            "status": result["ok"] and "ok" or "failed",
            "source": "fallback",
            "response": result["response"],
        }

    def run_audio_once(self, duration_seconds: float = 5.0, sample_rate: int = 16_000) -> dict[str, Any]:
        if not self.enable_audio or sd is None:
            return {
                "status": "audio-disabled",
                "response": "Audio capture is unavailable in this environment.",
                "transcript": "",
            }

        if not self.bridge.voice_runtime.available:
            return {
                "status": "audio-runtime-unavailable",
                "response": "Mark-LVI audio runtime is not available; install the optional audio dependencies.",
                "transcript": "",
            }

        try:
            recording = sd.rec(
                int(duration_seconds * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            transcript = self.bridge.voice_runtime.transcribe(recording, engine="whisper")
            if not transcript:
                transcript = ""
            final = self.run_text(transcript)
            return {
                "status": final["status"],
                "transcript": transcript,
                "response": final["response"],
            }
        except Exception as exc:  # pragma: no cover
            return {
                "status": "audio-failure",
                "response": f"Audio capture failed: {exc}",
                "transcript": "",
            }

    def speak(self, text: str, engine: str = "edge") -> bool:
        if not self.enable_audio or not self.bridge.voice_runtime.available:
            return False
        return self.bridge.voice_runtime.speak(text, engine=engine)

    def _fallback_command(self, text: str) -> dict[str, Any]:
        lowered = text.lower()

        if re.search(r"\b(status|estado|temperatura|cpu|ram|memoria|uptime)\b", lowered):
            meta = self.bridge.tool_registry.execute("system_status")
            if meta.ok:
                return {"ok": True, "response": self._format_tool_result(meta.result)}
            return {"ok": False, "response": meta.error or "Failed to read system status."}

        open_match = self._extract_open_app_name(text)
        if open_match:
            meta = self.bridge.tool_registry.execute("open_app", app_name=open_match)
            if meta.ok:
                return {"ok": True, "response": str(meta.result)}
            return {"ok": False, "response": meta.error or f"Failed to open {open_match}."}

        search_match = self._extract_search_query(text)
        if search_match:
            meta = self.bridge.tool_registry.execute("web_search", query=search_match, mode="search")
            if meta.ok:
                return {"ok": True, "response": str(meta.result)}
            return {"ok": False, "response": meta.error or f"Search failed for: {search_match}"}

        return {
            "ok": True,
            "response": (
                "I am running in fallback mode. The ULTRON core is not available in this environment, "
                "but the voice pipeline is ready for text commands and tool execution."
            ),
        }

    @staticmethod
    def _extract_open_app_name(text: str) -> str | None:
        patterns = [
            r"(?:abrir|open|launch|start)\s+(?:o\s+)?(?P<name>[a-zA-Z0-9._\- /]+)",
            r"(?:run|execute)\s+(?:the\s+)?(?P<name>[a-zA-Z0-9._\- /]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                name = match.group("name").strip(" \t\n")
                if name:
                    return name
        return None

    @staticmethod
    def _extract_search_query(text: str) -> str | None:
        patterns = [
            r"(?:pesquisar|search|buscar|procure)\s+(?:por\s+)?(?P<query>[\w\s\-.,/]+)",
            r"(?:research|look up|find)\s+(?:about\s+)?(?P<query>[\w\s\-.,/]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                query = match.group("query").strip(" \t\n")
                if query:
                    return query
        return None

    @staticmethod
    def _format_tool_result(data: Any) -> str:
        if isinstance(data, dict):
            parts = []
            for key, value in data.items():
                if value is None:
                    continue
                parts.append(f"{key}: {value}")
            return "; ".join(parts) if parts else "System status unavailable."
        return str(data)


def cli() -> None:
    runner = VoiceRunner(enable_audio=True)
    print("ULTRON 2.0 voice runner ready.")
    print("Type 'quit' to exit.")
    print("Type 'voice' to capture a short audio sample and transcribe it.")

    while True:
        try:
            raw = input("ultron> ").strip()
        except EOFError:
            print()
            break

        if raw.lower() in {"quit", "exit", "sair"}:
            break

        if raw.lower() == "voice":
            result = runner.run_audio_once(duration_seconds=4.0)
            print(result["response"])
            if result.get("transcript"):
                print(f"Transcript: {result['transcript']}")
            continue

        result = runner.run_text(raw)
        print(result["response"])


if __name__ == "__main__":
    cli()
