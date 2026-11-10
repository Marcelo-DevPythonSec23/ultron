"""TTS do ULTRON 2.0 — Gemini TTS com fallback para a voz do sistema.

Duas saídas reais, ambas verificadas:

* `GeminiTTS` — `generate_content` com `response_modalities=["AUDIO"]` e
  `speech_config` (modelos `*-tts`). Devolve PCM 16-bit; a taxa vem do
  `mime_type` da resposta (`audio/L16;rate=24000`), nunca é adivinhada.
* `SystemSpeaker` — a voz do próprio sistema: `spd-say --pipe-mode` no Linux,
  `say` no macOS, SAPI via PowerShell no Windows. Sem download e sem rede
  (mesma escolha de `Mark-LVI-main/providers/tts_system.py`).

Falha de TTS NUNCA derruba o turno: `VoicePipeline` captura a exceção e mantém
o texto da resposta disponível (Etapa 3 do plano aprovado).
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import platform
import re
import shutil
import tempfile
from typing import Any

from google import genai
from google.genai import types

from .audio_io import AudioUnavailableError, SubprocessPlayer
from .contracts import SPEAKER_SAMPLE_RATE

logger = logging.getLogger("ultron2.voice.tts")

TTS_MODEL_DEFAULT = "gemini-2.5-flash-preview-tts"
TTS_VOICE_DEFAULT = "Kore"

_RATE_RE = re.compile(r"rate=(\d+)", re.IGNORECASE)


def parse_mime_rate(mime_type: str | None, default: int = SPEAKER_SAMPLE_RATE) -> int:
    """Extrai a taxa de amostragem real do mime_type de áudio (L16)."""
    if not mime_type:
        return default
    match = _RATE_RE.search(mime_type)
    if not match:
        return default
    return int(match.group(1))


def _as_bytes(data: Any) -> bytes:
    """`inline_data.data` é bytes no SDK; aceita base64 por robustez."""
    if data is None:
        return b""
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    if isinstance(data, str):
        return base64.b64decode(data)
    return bytes(data)


class GeminiTTS:
    """Síntese via Gemini TTS + reprodução pelo dispositivo local."""

    def __init__(
        self,
        api_key: str | None,
        model: str = TTS_MODEL_DEFAULT,
        voice: str = TTS_VOICE_DEFAULT,
        player: SubprocessPlayer | None = None,
        client: "genai.Client | None" = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("GEMINI_API_KEY ausente —TTS Gemini não configurado")
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._player = player or SubprocessPlayer()
        self._client = client

    @property
    def model(self) -> str:
        return self._model

    def build_config(self) -> types.GenerateContentConfig:
        """Config REAL de TTS (response_modalities AUDIO + voz pré-construída)."""
        return types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self._voice
                    )
                )
            ),
        )

    def _ensure_client(self) -> "genai.Client":
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def synthesize(self, text: str) -> tuple[bytes, int]:
        """Texto -> (PCM 16-bit mono, taxa real)."""
        if not text.strip():
            return b"", SPEAKER_SAMPLE_RATE
        response = await self._ensure_client().aio.models.generate_content(
            model=self._model,
            contents=text,
            config=self.build_config(),
        )
        pcm, rate = extract_audio(response, default_rate=SPEAKER_SAMPLE_RATE)
        return pcm, rate

    async def speak(self, text: str) -> None:
        if not text.strip():
            return
        pcm, rate = await self.synthesize(text)
        if not pcm:
            raise AudioUnavailableError("Gemini TTS não devolveu áudio para o texto")
        await self._player.play(pcm, rate)


def extract_audio(response: Any, default_rate: int = SPEAKER_SAMPLE_RATE) -> tuple[bytes, int]:
    """Extrai o primeiro bloco de áudio de uma resposta de generate_content."""
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline is None:
                continue
            pcm = _as_bytes(getattr(inline, "data", None))
            if pcm:
                return pcm, parse_mime_rate(getattr(inline, "mime_type", None), default_rate)
    return b"", default_rate


class SystemSpeaker:
    """Voz do sistema operacional (sem rede)."""

    def __init__(self, language: str | None = None, timeout: float = 120.0) -> None:
        self._language = language
        self._timeout = timeout
        self._system = platform.system()

    @classmethod
    def available(cls) -> bool:
        system = platform.system()
        if system == "Linux":
            return shutil.which("spd-say") is not None
        if system == "Darwin":
            return shutil.which("say") is not None
        if system == "Windows":
            return shutil.which("powershell") is not None
        return False

    def _command(self, text: str) -> tuple[list[str], bytes | None, dict[str, str] | None]:
        """Retorna (argv, stdin, env) — texto NUNCA vai como argumento no Linux."""
        if self._system == "Linux":
            cmd = ["spd-say", "--wait", "--pipe-mode"]
            if self._language:
                cmd.extend(["--language", self._language])
            return cmd, (text + "\n").encode("utf-8"), None
        if self._system == "Darwin":
            cmd = ["say"]
            if self._language:
                cmd.extend(["-v", self._language])
            cmd.extend(["-f", self._write_temp(text)])
            return cmd, None, None
        if self._system == "Windows":
            path = self._write_temp(text)
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.Speak([IO.File]::ReadAllText($env:ULTRON2_TTS_FILE))"
            )
            env = dict(os.environ, ULTRON2_TTS_FILE=path)
            return ["powershell", "-NoProfile", "-Command", script], None, env
        raise AudioUnavailableError(f"sistema sem TTS suportado: {self._system}")

    @staticmethod
    def _write_temp(text: str) -> str:
        fd, path = tempfile.mkstemp(prefix="ultron2-tts-", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    async def speak(self, text: str) -> None:
        if not text.strip():
            return
        cmd, stdin, env = self._command(text.strip())
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            _, stderr = await asyncio.wait_for(
                proc.communicate(stdin), timeout=self._timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise AudioUnavailableError(f"TTS do sistema excedeu {self._timeout:.0f}s")
        if proc.returncode != 0:
            detail = (stderr or b"").decode("utf-8", "replace").strip()
            raise AudioUnavailableError(
                f"TTS do sistema falhou ({proc.returncode}): {detail or 'sem detalhe'}"
            )


class NullSpeaker:
    """Sem saída de áudio (modo texto/CI): registra que não falou."""

    def __init__(self) -> None:
        self.spoken: list[str] = []

    async def speak(self, text: str) -> None:
        self.spoken.append(text)
