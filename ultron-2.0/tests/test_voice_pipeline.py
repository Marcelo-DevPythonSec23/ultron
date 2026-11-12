"""Testes da camada de voz (Etapas C/D/F do AGENTS.md §13).

O que é validado de verdade:

* Teste C — texto reconhecido é encaminhado ao MESMO `process_text` do núcleo
  (não há caminho de conversa paralelo para voz).
* Teste D — falha de TTS não derruba o turno: o texto da resposta permanece.
* Teste F — fluxo completo áudio -> STT -> núcleo -> resposta -> TTS sem criar
  uma segunda conversa; o conversation_id é o mesmo do histórico do lain.

Os fakes substituem apenas os DISPOSITIVOS (microfone, alto-falante) e o
transporte de STT; o núcleo, o orquestrador, o provedor e a persistência são
os reais (banco em memória, ScriptedProvider).
"""

from __future__ import annotations

import ultron_2_0  # sys.path lain + Mark-LVI
from ultron_2_0.orchestrator_bridge import OrchestratorBridge
from ultron_2_0.voice.contracts import VoiceTurn
from ultron_2_0.voice.pipeline import VoicePipeline

from tests.fakes import ScriptedProvider


class FakeSpeaker:
    def __init__(self, fail_with: Exception | None = None) -> None:
        self.spoken: list[str] = []
        self._fail_with = fail_with

    async def speak(self, text: str) -> None:
        if self._fail_with is not None:
            raise self._fail_with
        self.spoken.append(text)


class FakeTranscriber:
    def __init__(self, transcript: str) -> None:
        self.transcript = transcript
        self.calls: list[tuple[bytes, str]] = []

    async def transcribe(self, audio: bytes, mime_type: str = "audio/wav") -> str:
        self.calls.append((audio, mime_type))
        return self.transcript


def _bridge() -> OrchestratorBridge:
    return OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )


def test_stt_entra_no_mesmo_process_text_do_nucleo():
    """Teste C: fala -> transcript -> orquestrador do lain -> persistência."""
    with _bridge() as bridge:
        scripted = ScriptedProvider(["luzes acesas, senhor."])
        bridge.runtime.register_provider(scripted)
        speaker = FakeSpeaker()
        pipeline = VoicePipeline(bridge, speaker=speaker)

        turn = asyncio_run(pipeline.handle_transcript("acenda as luzes"))

        assert isinstance(turn, VoiceTurn)
        assert turn.response_text == "luzes acesas, senhor."
        assert turn.conversation_id == bridge.conversation_id
        assert turn.provider == "mock"
        assert turn.spoken is True
        assert speaker.spoken == ["luzes acesas, senhor."]

        # A mensagem do usuário foi a MESMA que o núcleo persistiu (não um eco).
        history = asyncio_run(
            bridge.runtime.orchestrator.chat_service.get_recent_chat_messages(
                conversation_id=turn.conversation_id
            )
        )
        contents = [m.content for m in history]
        assert "acenda as luzes" in contents
        assert "luzes acesas, senhor." in contents


def test_falha_de_tts_preserva_o_texto_da_resposta():
    """Teste D: dispositivo de áudio quebrado não interrompe o núcleo."""
    with _bridge() as bridge:
        bridge.runtime.register_provider(ScriptedProvider(["resposta que importa"]))
        speaker = FakeSpeaker(fail_with=RuntimeError("device disconnected"))
        pipeline = VoicePipeline(bridge, speaker=speaker)

        turn = asyncio_run(pipeline.handle_transcript("diga algo"))

        assert turn.response_text == "resposta que importa"
        assert turn.spoken is False
        assert turn.tts_error is not None
        assert "device disconnected" in turn.tts_error
        # O turno continua persistido no histórico do núcleo.
        history = asyncio_run(
            bridge.runtime.orchestrator.chat_service.get_recent_chat_messages(
                conversation_id=turn.conversation_id
            )
        )
        assert "resposta que importa" in [m.content for m in history]


def test_voz_e_texto_compartilham_uma_unica_conversa():
    """Teste F: dois turnos de voz -> uma única conversa (nada de histórico duplo)."""
    with _bridge() as bridge:
        bridge.runtime.register_provider(ScriptedProvider(["primeira", "segunda"]))
        pipeline = VoicePipeline(bridge, speaker=FakeSpeaker())

        t1 = asyncio_run(pipeline.handle_transcript("turno falado 1"))
        t2 = asyncio_run(pipeline.handle_transcript("turno falado 2"))

        assert t1.conversation_id == t2.conversation_id == bridge.conversation_id
        _, total = asyncio_run(
            bridge.runtime.orchestrator.chat_service.list_conversations()
        )
        assert total == 1

        # Turno de texto depois da voz cai na MESMA conversa da interface.
        r3 = bridge.process_text("turno digitado 3")
        assert r3.conversation_id == t1.conversation_id


def test_transcricao_vazia_nao_chama_o_modelo():
    with _bridge() as bridge:
        scripted = ScriptedProvider(["não deveria ser chamado"])
        bridge.runtime.register_provider(scripted)
        pipeline = VoicePipeline(bridge, speaker=FakeSpeaker())

        turn = asyncio_run(pipeline.handle_transcript("   "))

        assert turn.response_text == ""
        assert turn.metadata["error"] == "empty_transcript"
        assert len(scripted.calls) == 0


def test_handle_audio_usa_o_transcritor_e_o_mesmo_caminho():
    """Teste C/F: buffer de áudio -> STT em lote -> núcleo -> resposta falada."""
    with _bridge() as bridge:
        scripted = ScriptedProvider(["transcrição executada"])
        bridge.runtime.register_provider(scripted)
        transcriber = FakeTranscriber("qual a temperatura?")
        speaker = FakeSpeaker()
        pipeline = VoicePipeline(
            bridge, speaker=speaker, transcriber=transcriber
        )

        turn = asyncio_run(pipeline.handle_audio(b"RIFF...falso", "audio/wav"))

        assert transcriber.calls == [(b"RIFF...falso", "audio/wav")]
        assert turn.transcript == "qual a temperatura?"
        assert turn.response_text == "transcrição executada"
        assert speaker.spoken == ["transcrição executada"]
        assert len(scripted.calls) == 1


def test_handle_audio_sem_transcritor_falha_alto():
    with _bridge() as bridge:
        pipeline = VoicePipeline(bridge)
        try:
            asyncio_run(pipeline.handle_audio(b"x"))
        except RuntimeError as exc:
            assert "transcritor" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("esperava RuntimeError")


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
