from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


class VoiceRuntime:
    """Bridge for the Mark-LVI voice stack.

    This class intentionally does not replace the original runtime. Instead, it
    exposes an adapter layer for the ULTRON core to reuse the original STT/TTS
    implementations while keeping the runtime isolated from the conversation engine.
    """

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.mark_lvi_root = self.project_root / "Mark-LVI-main"
        self.available = False
        self.stt = None
        self.tts = None
        self.errors: list[str] = []
        self._load_runtime()

    def _load_runtime(self) -> None:
        if not self.mark_lvi_root.exists():
            self.errors.append(f"Mark-LVI project not found at {self.mark_lvi_root}")
            return

        root_str = str(self.mark_lvi_root)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)

        try:
            from core.stt import WhisperSTT, VoskSTT
            from core.tts import KokoroTTSEngine, EdgeTTSEngine

            self.stt = {
                "whisper": WhisperSTT,
                "vosk": VoskSTT,
            }
            self.tts = {
                "kokoro": KokoroTTSEngine,
                "edge": EdgeTTSEngine,
            }
            self.available = True
        except Exception as exc:  # pragma: no cover - optional runtime integration
            self.available = False
            self.errors.append(f"Failed to load Mark-LVI speech stack: {exc}")

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "stt_engines": list(self.stt.keys()) if self.stt else [],
            "tts_engines": list(self.tts.keys()) if self.tts else [],
            "errors": self.errors,
        }

    def transcribe(self, audio: Any, engine: str = "whisper", **kwargs: str) -> str:
        if not self.available or not self.stt:
            return ""
        try:
            engine_impl = self.stt.get(engine)
            if engine_impl is None:
                raise KeyError(f"Unknown STT engine: {engine}")
            recognizer = engine_impl(**kwargs)
            return recognizer.transcribe(audio)
        except Exception as exc:  # pragma: no cover
            self.errors.append(f"STT failed with {engine}: {exc}")
            return ""

    def speak(self, text: str, engine: str = "edge", **kwargs: str) -> bool:
        if not self.available or not self.tts:
            return False
        try:
            engine_impl = self.tts.get(engine)
            if engine_impl is None:
                raise KeyError(f"Unknown TTS engine: {engine}")
            speaker = engine_impl(**kwargs)
            speaker.speak(text)
            return True
        except Exception as exc:  # pragma: no cover
            self.errors.append(f"TTS failed with {engine}: {exc}")
            return False
