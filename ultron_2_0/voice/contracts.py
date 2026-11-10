"""Contratos da camada de voz do ULTRON 2.0 (Etapa 3).

A voz é uma INTERFACE, não um segundo cérebro. Independentemente do motor de
STT/TTS escolhido, o texto reconhecido entra pelo MESMO
`OrchestratorBridge.process_text` usado pela CLI de texto, que por sua vez roda
o `Orchestrator` original do lain — único ciclo conversacional e único
histórico durável (docs/INTEGRATION_AUDIT.md §5.1).

Consequência de projeto: um motor que decidisse sozinho (como a sessão Gemini
Live do Mark-LVI, que responde e chama tools por conta própria) NÃO é usado
como orquestrador. O Gemini Live entra apenas como serviço de transcrição
(áudio -> texto) e o texto segue o caminho do núcleo.

O texto da resposta é SEMPRE devolvido, mesmo quando a síntese falha: TTS é uma
saída opcional, a conversa nunca depende dele.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol, runtime_checkable

# Taxas fixas do Gemini Live (as mesmas do Mark-LVI main.py:112-113).
MIC_SAMPLE_RATE = 16_000
SPEAKER_SAMPLE_RATE = 24_000
SAMPLE_WIDTH = 2  # 16-bit signed little-endian
CHANNELS = 1


@dataclass(slots=True)
class VoiceTurn:
    """Resultado de um turno de voz, com o texto preservado sempre."""

    transcript: str
    response_text: str = ""
    spoken: bool = False
    tts_error: str | None = None
    conversation_id: str | None = None
    provider: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.response_text) and self.metadata.get("error") is None

    def as_dict(self) -> dict[str, Any]:
        return {
            "transcript": self.transcript,
            "response_text": self.response_text,
            "spoken": self.spoken,
            "tts_error": self.tts_error,
            "conversation_id": self.conversation_id,
            "provider": self.provider,
            "model": self.model,
            "metadata": self.metadata,
        }


@runtime_checkable
class Microphone(Protocol):
    """Fonte de PCM 16-bit mono (16 kHz) em chunks."""

    def chunks(self) -> AsyncIterator[bytes]: ...


@runtime_checkable
class BatchTranscriber(Protocol):
    """STT de um buffer de áudio completo (arquivo/utterance)."""

    async def transcribe(self, audio: bytes, mime_type: str = "audio/wav") -> str: ...


@runtime_checkable
class Speaker(Protocol):
    """Saída de fala: recebe o texto da resposta e o sintetiza/reproduz."""

    async def speak(self, text: str) -> None: ...
