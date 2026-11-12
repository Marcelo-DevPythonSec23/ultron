"""Camada de voz do ULTRON 2.0 (Etapa 3).

Regra de autoridade: a voz é apenas interface. STT entrega texto ao MESMO
`OrchestratorBridge.process_text` da CLI (um único histórico no núcleo do lain)
e o texto da resposta é sempre preservado, com ou sem TTS.

Uso:

    python -m ultron_2_0.voice --list-devices
    python -m ultron_2_0.voice --no-tts
    python -m ultron_2_0.voice --audio fala.wav --no-tts
"""

from __future__ import annotations

from .contracts import (
    BatchTranscriber,
    Microphone,
    Speaker,
    VoiceTurn,
)
from .pipeline import VoicePipeline

__all__ = [
    "BatchTranscriber",
    "Microphone",
    "Speaker",
    "VoiceTurn",
    "VoicePipeline",
]
