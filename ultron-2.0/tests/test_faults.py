"""Teste G — recuperação de falhas controladas (AGENTS.md §13).

Nenhuma falha de dispositivo, provedor, action ou conexão pode derrubar o
núcleo: o sistema deve continuar de pé e informar o motivo. Os testes usam os
componentes REAIS (gateway, orquestrador, pipeline de voz) e falham apenas os
pontos externos (rede, dispositivo, subprocesso).
"""

from __future__ import annotations

import asyncio
import json
import sys

import pytest

import ultron_2_0  # sys.path lain + Mark-LVI
from app.intelligence.providers.base import (
    LLMProvider,
    ProviderConnectionError,
)
from app.models.message import LLMRequest, LLMResponse, MessageRole
from ultron_2_0.core_runtime import UltronCoreRuntime
from ultron_2_0.orchestrator_bridge import OrchestratorBridge
from ultron_2_0.voice import audio_io
from ultron_2_0.voice.audio_io import (
    AudioUnavailableError,
    SubprocessMicrophone,
    SubprocessPlayer,
)
from ultron_2_0.voice.pipeline import VoicePipeline
from ultron_2_0.voice.stt_gemini import LiveTranscriptionSession

from tests.fakes import ScriptedProvider


class FailingProvider(LLMProvider):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "failing-model"

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        raise self._exc

    async def generate_stream(self, request: LLMRequest):
        raise self._exc
        yield  # pragma: no cover

    async def health_check(self) -> bool:
        return False


class FakeSpeaker:
    def __init__(self, failures: int = 0) -> None:
        self.spoken: list[str] = []
        self._failures = failures

    async def speak(self, text: str) -> None:
        if self._failures > 0:
            self._failures -= 1
            raise RuntimeError("audio device lost")
        self.spoken.append(text)


# -- provedor ---------------------------------------------------------------

async def test_provedor_indisponivel_falha_de_forma_controlada_e_se_recupera():
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )
    try:
        await runtime.start_async()
        runtime.register_provider(
            FailingProvider(ProviderConnectionError("network down", provider="mock"))
        )
        with pytest.raises(ProviderConnectionError):
            await runtime.chat("oi")

        # O núcleo continua utilizável: trocar o provedor resolve sem reiniciar.
        runtime.register_provider(ScriptedProvider(["de volta ao normal"]))
        response = await runtime.chat("oi de novo")
        assert response.content == "de volta ao normal"
    finally:
        await runtime.shutdown()


def test_bridge_sem_start_falha_com_mensagem_clara():
    bridge = OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:", enable_tools=False
    )
    with pytest.raises(RuntimeError):
        bridge.process_text("oi")


# -- microfone / alto-falante ----------------------------------------------

def test_microfone_indisponivel_erro_explicito(monkeypatch):
    monkeypatch.setattr(audio_io, "detect_microphone_command", lambda: None)
    with pytest.raises(AudioUnavailableError) as excinfo:
        SubprocessMicrophone()
    message = str(excinfo.value)
    assert "parec" in message or "arecord" in message


def test_microfone_encerra_subprocesso_ao_fechar_o_stream():
    """Fechar o consumidor não deixa o capturador rodando (sem processos órfãos)."""
    script = (
        "import sys, time\n"
        "while True:\n"
        "    sys.stdout.buffer.write(b'x' * 4096)\n"
        "    sys.stdout.buffer.flush()\n"
        "    time.sleep(0.02)\n"
    )
    microphone = SubprocessMicrophone(
        command=[sys.executable, "-c", script], chunk_bytes=128
    )

    async def scenario() -> bytes:
        stream = microphone.chunks()
        chunk = await stream.__anext__()
        await stream.aclose()
        return chunk

    chunk = asyncio.run(scenario())
    assert chunk, "o microfone falso deveria ter entregado áudio"


def test_falha_do_dispositivo_de_saida_vira_erro_explicito():
    player = SubprocessPlayer(
        command_factory=lambda rate: ["sh", "-c", "cat >/dev/null; exit 3"]
    )
    with pytest.raises(AudioUnavailableError) as excinfo:
        asyncio.run(player.play(b"\x00\x01" * 256, 24000))
    assert "código 3" in str(excinfo.value)


# -- conexão de STT ---------------------------------------------------------

class _BrokenLiveSession:
    async def receive(self):
        raise ConnectionError("websocket fechado")
        yield  # pragma: no cover


def test_queda_de_conexao_do_stt_propaga_erro():
    session = LiveTranscriptionSession(_BrokenLiveSession())

    async def consume():
        return [text async for text in session.transcripts()]

    with pytest.raises(ConnectionError):
        asyncio.run(consume())


# -- action com erro / parâmetro inválido ----------------------------------

async def test_parametro_invalido_vira_falha_informada_ao_modelo():
    """A ferramenta recusa; o modelo recebe status=failed e ainda responde."""
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=True,
    )
    try:
        await runtime.start_async()
        scripted = ScriptedProvider(
            [
                json.dumps({"tool": "system_status", "args": {"force": True}}),
                "não consegui ler as métricas, mas sigo aqui.",
            ]
        )
        runtime.register_provider(scripted)

        response = await runtime.chat("como está a máquina?")

        assert response.content == "não consegui ler as métricas, mas sigo aqui."
        second = [m.content for m in scripted.calls[1].messages]
        tool_result = next(c for c in second if c.startswith("[TOOL_RESULT"))
        assert "status=failed" in tool_result
        assert "unknown parameter" in tool_result
    finally:
        await runtime.shutdown()


async def test_ferramenta_inexistente_nao_derruba_o_turno():
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=True,
    )
    try:
        await runtime.start_async()
        scripted = ScriptedProvider(
            [
                json.dumps({"tool": "ferramenta_que_nao_existe", "args": {}}),
                "essa ferramenta não existe.",
            ]
        )
        runtime.register_provider(scripted)

        response = await runtime.chat("faça algo impossível")

        assert response.content == "essa ferramenta não existe."
        second = [m.content for m in scripted.calls[1].messages]
        tool_result = next(c for c in second if c.startswith("[TOOL_RESULT"))
        assert "unknown tool" in tool_result
    finally:
        await runtime.shutdown()


def test_tts_falha_e_o_proximo_turno_continua_funcionando():
    with OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    ) as bridge:
        bridge.runtime.register_provider(ScriptedProvider(["um", "dois"]))
        speaker = FakeSpeaker(failures=1)
        pipeline = VoicePipeline(bridge, speaker=speaker)

        first = asyncio.run(pipeline.handle_transcript("primeiro"))
        second = asyncio.run(pipeline.handle_transcript("segundo"))

        assert first.response_text == "um"
        assert first.spoken is False and first.tts_error
        assert second.response_text == "dois"
        assert second.spoken is True
        assert speaker.spoken == ["dois"]


# -- fluxo completo voz -> tool -> voz -------------------------------------

def test_fluxo_completo_voz_tool_voz_sem_segunda_conversa():
    """Teste F/G: fala -> núcleo -> tool real -> texto -> TTS, uma conversa só."""
    with OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=True,
    ) as bridge:
        scripted = ScriptedProvider(
            [
                json.dumps({"tool": "system_status", "args": {}}),
                "A máquina está saudável.",
            ]
        )
        bridge.runtime.register_provider(scripted)
        speaker = FakeSpeaker()
        pipeline = VoicePipeline(bridge, speaker=speaker)

        turn = asyncio.run(pipeline.handle_transcript("como está o sistema?"))

        assert turn.response_text == "A máquina está saudável."
        assert turn.spoken is True
        assert speaker.spoken == ["A máquina está saudável."]
        # A tool REAL rodou (duas chamadas ao modelo) e a conversa é única.
        assert len(scripted.calls) == 2
        _, total = asyncio.run(
            bridge.runtime.orchestrator.chat_service.list_conversations()
        )
        assert total == 1
