"""Dispositivos de áudio do ULTRON 2.0 — sem inventar APIs.

Captura e reprodução usam as ferramentas que o sistema realmente tem
(`parec`/`arecord` para o microfone, `aplay`/`paplay` para os alto-falantes),
em subprocessos assíncronos. Se nada estiver disponível, o erro é explícito —
nunca um silêncio que parece funcionar (mesma lição de
`Mark-LVI-main/providers/tts_system.py`: um fallback que se cala é pior do que
um que diz o que está errado).

`numpy`/`sounddevice` NÃO são exigidos: este módulo trabalha com PCM cru.
"""

from __future__ import annotations

import asyncio
import io
import shutil
import wave
from typing import AsyncIterator

from .contracts import CHANNELS, MIC_SAMPLE_RATE, SAMPLE_WIDTH, SPEAKER_SAMPLE_RATE


class AudioUnavailableError(RuntimeError):
    """Nenhum backend de áudio utilizável foi encontrado."""


def wav_bytes(pcm: bytes, sample_rate: int = SPEAKER_SAMPLE_RATE) -> bytes:
    """Empacota PCM 16-bit mono em um WAV em memória."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(SAMPLE_WIDTH)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buf.getvalue()


def detect_microphone_command() -> list[str] | None:
    """Comando de captura ao vivo em PCM cru, se houver um disponível."""
    if shutil.which("parec"):
        return [
            "parec",
            "--format=s16le",
            f"--rate={MIC_SAMPLE_RATE}",
            f"--channels={CHANNELS}",
            "--raw",
        ]
    if shutil.which("arecord"):
        return [
            "arecord",
            "-q",
            "-f", "S16_LE",
            "-r", str(MIC_SAMPLE_RATE),
            "-c", str(CHANNELS),
            "-t", "raw",
        ]
    return None


def detect_player_command(sample_rate: int) -> list[str] | None:
    """Comando de reprodução de PCM cru 16-bit mono, se houver um disponível."""
    if shutil.which("aplay"):
        return [
            "aplay",
            "-q",
            "-t", "raw",
            "-f", "S16_LE",
            "-r", str(sample_rate),
            "-c", str(CHANNELS),
        ]
    if shutil.which("paplay"):
        return [
            "paplay",
            "--raw",
            "--format=s16le",
            f"--rate={sample_rate}",
            f"--channels={CHANNELS}",
        ]
    return None


def audio_capabilities() -> dict[str, object]:
    """Diagnóstico real do que esta máquina oferece (para `/status` e logs)."""
    mic = detect_microphone_command()
    player = detect_player_command(SPEAKER_SAMPLE_RATE)
    return {
        "microphone": mic[0] if mic else None,
        "speaker": player[0] if player else None,
        "sample_rate_in": MIC_SAMPLE_RATE,
        "sample_rate_out": SPEAKER_SAMPLE_RATE,
        "tools_available": {
            name: bool(shutil.which(name))
            for name in ("parec", "arecord", "pw-record", "aplay", "paplay", "spd-say", "say")
        },
    }


class SubprocessMicrophone:
    """Microfone via subprocesso (parec/arecord), streaming PCM 16 kHz mono."""

    def __init__(
        self,
        command: list[str] | None = None,
        chunk_bytes: int = 3200,  # 100 ms a 16 kHz/16-bit mono
    ) -> None:
        self._command = command or detect_microphone_command()
        self._chunk_bytes = max(int(chunk_bytes), SAMPLE_WIDTH * CHANNELS)
        if self._command is None:
            raise AudioUnavailableError(
                "nenhum capturador de microfone encontrado "
                "(instale pulseaudio-utils/`parec` ou alsa-utils/`arecord`)"
            )

    @classmethod
    def available(cls) -> bool:
        return detect_microphone_command() is not None

    async def chunks(self) -> AsyncIterator[bytes]:
        """Entrega o PCM conforme o microfone produz; encerra o processo no fim."""
        proc = await asyncio.create_subprocess_exec(
            *self._command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            assert proc.stdout is not None
            while True:
                chunk = await proc.stdout.read(self._chunk_bytes)
                if not chunk:
                    break
                yield chunk
        finally:
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2)
                except asyncio.TimeoutError:  # pragma: no cover - defesa
                    proc.kill()
                    await proc.wait()


class SubprocessPlayer:
    """Reprodução de PCM 16-bit mono via aplay/paplay."""

    def __init__(self, command_factory=None) -> None:
        self._command_factory = command_factory or detect_player_command

    @classmethod
    def available(cls) -> bool:
        return detect_player_command(SPEAKER_SAMPLE_RATE) is not None

    async def play(self, pcm: bytes, sample_rate: int = SPEAKER_SAMPLE_RATE) -> None:
        if not pcm:
            return
        command = self._command_factory(sample_rate)
        if command is None:
            raise AudioUnavailableError(
                "nenhum reprodutor de áudio encontrado "
                "(instale alsa-utils/`aplay` ou pulseaudio-utils/`paplay`)"
            )
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdin is not None
        _, stderr = await proc.communicate(pcm)
        if proc.returncode != 0:
            detail = (stderr or b"").decode("utf-8", "replace").strip()
            raise AudioUnavailableError(
                f"reprodutor saiu com código {proc.returncode}: {detail or 'sem detalhe'}"
            )
