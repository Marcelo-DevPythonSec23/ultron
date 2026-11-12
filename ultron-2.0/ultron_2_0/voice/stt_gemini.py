"""STT com Gemini Live — apenas o serviço de transcrição, nunca o cérebro.

O ciclo de voz real do Mark-LVI (`main.py`) é uma sessão Gemini Live
bidirecional que também raciocina e chama tools. Reproduzir esse ciclo como
orquestrador criaria um SEGUNDO mecanismo de decisão/histórico, proibido pelo
AGENTS.md. A extração correta é a parte de áudio: aqui o Live é aberto com
`response_modalities=["TEXT"]` e `input_audio_transcription` ligado, e APENAS
a transcrição da fala do usuário é consumida. O texto segue para
`OrchestratorBridge.process_text` (núcleo do lain).

APIs verificadas no `google-genai` 3.0.0 instalado (não inventadas):

    types.LiveConnectConfig(response_modalities=[...],
                            input_audio_transcription=AudioTranscriptionConfig(),
                            system_instruction=...)
    client.aio.live.connect(model=..., config=...)      (async context manager)
    session.send_realtime_input(audio=types.Blob(data=..., mime_type=...))
    session.receive() -> LiveServerMessage
    message.server_content.input_transcription.text / .finished
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable

from google import genai
from google.genai import types

from .contracts import MIC_SAMPLE_RATE

logger = logging.getLogger("ultron2.voice.stt")

# Modelo Live usado pelo Mark-LVI (main.py:110). Configurável por CLI/env.
LIVE_MODEL_DEFAULT = "gemini-3.1-flash-live-preview"
# Modelo de texto para transcrição em lote (mesmo padrão do lain).
BATCH_MODEL_DEFAULT = "gemini-3.5-flash"

_TRANSCRIBE_INSTRUCTION = (
    "You are a speech-to-text engine. Transcribe the user's speech verbatim, "
    "in the language spoken. Do not answer, do not add commentary. If the "
    "audio is silence or noise, output nothing."
)


class GeminiLiveSTT:
    """Transcrição em streaming via Gemini Live (áudio -> texto)."""

    def __init__(
        self,
        api_key: str | None,
        model: str = LIVE_MODEL_DEFAULT,
        language_code: str | None = None,
        api_version: str = "v1alpha",
        client: "genai.Client | None" = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("GEMINI_API_KEY ausente —STT Gemini não configurado")
        self._api_key = api_key
        self._model = model
        self._language_code = language_code
        self._api_version = api_version
        self._client = client

    @property
    def model(self) -> str:
        return self._model

    def build_config(self) -> types.LiveConnectConfig:
        """Config REAL do Live: só transcrição de entrada, sem tools."""
        transcription = types.AudioTranscriptionConfig(
            language_codes=[self._language_code] if self._language_code else None
        )
        return types.LiveConnectConfig(
            response_modalities=["TEXT"],
            input_audio_transcription=transcription,
            system_instruction=_TRANSCRIBE_INSTRUCTION,
        )

    def _ensure_client(self) -> "genai.Client":
        if self._client is None:
            self._client = genai.Client(
                api_key=self._api_key,
                http_options={"api_version": self._api_version},
            )
        return self._client

    @asynccontextmanager
    async def connect(self) -> AsyncIterator["LiveTranscriptionSession"]:
        client = self._ensure_client()
        async with client.aio.live.connect(
            model=self._model, config=self.build_config()
        ) as session:
            logger.info("sessão Live de transcrição aberta (model=%s)", self._model)
            yield LiveTranscriptionSession(session)


class LiveTranscriptionSession:
    """Sessão aberta: envia áudio e entrega transcrições finais."""

    def __init__(self, session) -> None:
        self._session = session

    async def send_audio(self, chunk: bytes) -> None:
        """Envia um bloco PCM 16-bit mono 16 kHz."""
        if not chunk:
            return
        await self._session.send_realtime_input(
            audio=types.Blob(
                data=chunk,
                mime_type=f"audio/pcm;rate={MIC_SAMPLE_RATE}",
            )
        )

    async def transcripts(
        self,
        on_partial: Callable[[str], None] | None = None,
    ) -> AsyncIterator[str]:
        """Entrega a transcrição acumulada de cada turno de fala.

        `input_transcription.text` chega em pedaços; `.finished` marca o fim do
        turno. `interim_input_transcription` é repassado opcionalmente como
        parcial (para UI), mas nunca vira um turno por si só.
        """
        buffer: list[str] = []
        async for message in self._session.receive():
            content = getattr(message, "server_content", None)
            if content is None:
                continue

            interim = getattr(content, "interim_input_transcription", None)
            if interim is not None and getattr(interim, "text", None) and on_partial:
                on_partial(interim.text)

            transcription = getattr(content, "input_transcription", None)
            text = getattr(transcription, "text", None) if transcription is not None else None
            if text:
                buffer.append(text)

            # `finished` marca o fim da transcrição, mas alguns servidores só
            # fecham o turno em `turn_complete` — os dois encerram o acúmulo.
            finished = (
                bool(getattr(transcription, "finished", False))
                if transcription is not None
                else False
            )
            if buffer and (finished or getattr(content, "turn_complete", False)):
                final = "".join(buffer).strip()
                buffer.clear()
                if final:
                    yield final


class GeminiBatchTranscriber:
    """STT de um buffer completo (arquivo WAV/PCM), via generate_content."""

    def __init__(
        self,
        api_key: str | None,
        model: str = BATCH_MODEL_DEFAULT,
        client: "genai.Client | None" = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("GEMINI_API_KEY ausente —STT Gemini não configurado")
        self._api_key = api_key
        self._model = model
        self._client = client

    def _ensure_client(self) -> "genai.Client":
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def transcribe(self, audio: bytes, mime_type: str = "audio/wav") -> str:
        response = await self._ensure_client().aio.models.generate_content(
            model=self._model,
            contents=[
                types.Part.from_bytes(data=audio, mime_type=mime_type),
                _TRANSCRIBE_INSTRUCTION,
            ],
        )
        text = getattr(response, "text", None)
        return (text or "").strip()
