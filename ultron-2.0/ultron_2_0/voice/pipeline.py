"""Pipeline de voz do ULTRON 2.0 — uma conversa só, texto sempre preservado.

    áudio -> STT (Gemini Live) -> texto
                                 |
                                 v
                    OrchestratorBridge.process_text   <- MESMO caminho da CLI
                                 |
                                 v
                    Orchestrator do lain (único histórico/memória)
                                 |
                    +------------+------------+
                    |                         |
                 texto (sempre)            TTS (opcional)

Não existe caminho alternativo para voz: o `conversation_id` da sessão é o
mesmo mantido pelo `OrchestratorBridge`, então áudio e texto caem na MESMA
conversa persistida pelo núcleo.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from .contracts import BatchTranscriber, Speaker, VoiceTurn

logger = logging.getLogger("ultron2.voice.pipeline")


class VoicePipeline:
    """Executa turnos de voz pelo núcleo ULTRON (nunca por um segundo cérebro)."""

    def __init__(
        self,
        bridge: Any,
        speaker: Speaker | None = None,
        transcriber: BatchTranscriber | None = None,
        on_transcript: Callable[[str], None] | None = None,
        on_response: Callable[[VoiceTurn], None] | None = None,
    ) -> None:
        self._bridge = bridge
        self._speaker = speaker
        self._transcriber = transcriber
        self._on_transcript = on_transcript
        self._on_response = on_response

    async def handle_transcript(self, transcript: str) -> VoiceTurn:
        """Turno a partir de texto já reconhecido (voz ou digitação)."""
        text = (transcript or "").strip()
        if not text:
            return VoiceTurn(
                transcript="",
                metadata={"error": "empty_transcript", "skipped": True},
            )

        if self._on_transcript is not None:
            self._on_transcript(text)

        # process_text bloqueia no loop dedicado do núcleo -> thread.
        response = await asyncio.to_thread(self._bridge.process_text, text)
        response_text = response.content or ""
        turn = VoiceTurn(
            transcript=text,
            response_text=response_text,
            conversation_id=getattr(response, "conversation_id", None),
            provider=getattr(response, "provider", None),
            model=getattr(response, "model", None),
        )

        if self._speaker is not None:
            try:
                await self._speaker.speak(response_text)
                turn.spoken = True
            except Exception as exc:  # TTS é opcional: o texto permanece
                turn.spoken = False
                turn.tts_error = f"{type(exc).__name__}: {exc}"
                logger.warning("TTS falhou (texto preservado): %s", turn.tts_error)

        if self._on_response is not None:
            self._on_response(turn)
        return turn

    async def handle_audio(
        self, audio: bytes, mime_type: str = "audio/wav"
    ) -> VoiceTurn:
        """Turno a partir de um buffer de áudio (STT em lote)."""
        if self._transcriber is None:
            raise RuntimeError(
                "pipeline sem transcritor — use handle_transcript() ou "
                "passe transcriber= para handle_audio()"
            )
        transcript = await self._transcriber.transcribe(audio, mime_type)
        return await self.handle_transcript(transcript)
