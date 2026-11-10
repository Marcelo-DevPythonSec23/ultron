"""Testes unitários dos adaptadores de voz (STT/TTS/áudio), sem rede.

Validam as APIs REAIS do google-genai 3.0.0 instalado (configs construídas com
os tipos do SDK) e o parsing das respostas; nenhuma chamada de rede é feita.
"""

from __future__ import annotations

import ultron_2_0  # noqa: F401 — sys.path lain + Mark-LVI
from google.genai import types

from ultron_2_0.voice.audio_io import (
    audio_capabilities,
    detect_microphone_command,
    detect_player_command,
    wav_bytes,
)
from ultron_2_0.voice.contracts import MIC_SAMPLE_RATE, SPEAKER_SAMPLE_RATE
from ultron_2_0.voice.stt_gemini import GeminiBatchTranscriber, GeminiLiveSTT
from ultron_2_0.voice.tts import (
    GeminiTTS,
    NullSpeaker,
    SystemSpeaker,
    extract_audio,
    parse_mime_rate,
)


# -- STT -------------------------------------------------------------------

def test_live_stt_config_e_real_e_so_transcreve():
    stt = GeminiLiveSTT("chave-falsa")
    config = stt.build_config()
    assert isinstance(config, types.LiveConnectConfig)
    assert list(config.response_modalities) == ["TEXT"]
    assert config.input_audio_transcription is not None
    # Não há tool calling nem resposta em áudio: o Live aqui não decide nada.
    assert config.tools is None
    assert config.system_instruction


def test_live_stt_sem_chave_falha_cedo():
    try:
        GeminiLiveSTT(None)
    except ValueError as exc:
        assert "GEMINI_API_KEY" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("esperava ValueError")


class _FakeLiveSession:
    def __init__(self, messages):
        self._messages = messages
        self.sent: list[bytes] = []

    async def send_realtime_input(self, *, audio=None):
        self.sent.append(audio.data)

    async def receive(self):
        for message in self._messages:
            yield message


def _live_message(text=None, finished=False, interim=None, turn_complete=False):
    transcription = types.Transcription(text=text, finished=finished) if text is not None else None
    interim_tr = types.Transcription(text=interim) if interim is not None else None
    content = types.LiveServerContent(
        input_transcription=transcription,
        interim_input_transcription=interim_tr,
        turn_complete=turn_complete,
    )
    return types.LiveServerMessage(server_content=content)


def test_live_session_envia_pcm_e_entrega_apenas_turnos_finais():
    import asyncio

    from ultron_2_0.voice.stt_gemini import LiveTranscriptionSession

    messages = [
        _live_message(text="olá ", finished=False),
        _live_message(text="mundo", finished=True),
        _live_message(turn_complete=True),  # sem buffer: nada a emitir
        _live_message(text="segundo turno", turn_complete=True),
    ]
    fake = _FakeLiveSession(messages)
    session = LiveTranscriptionSession(fake)

    async def scenario():
        await session.send_audio(b"\x00\x01")
        partials: list[str] = []
        finals = [t async for t in session.transcripts(on_partial=partials.append)]
        return partials, finals

    partials, finals = asyncio.run(scenario())
    assert fake.sent == [b"\x00\x01"]
    assert finals == ["olá mundo", "segundo turno"]


class _FakeContent:
    def __init__(self, text): self.text = text


class _FakeResponse:
    def __init__(self, text): self.text = text


class _FakeAsyncModels:
    def __init__(self, text): self._text = text; self.kwargs = None
    async def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return _FakeResponse(self._text)


class _FakeAio:
    def __init__(self, models): self.models = models


class _FakeClient:
    def __init__(self, text): self.aio = _FakeAio(_FakeAsyncModels(text))


def test_batch_stt_envia_audio_e_instrucao():
    import asyncio

    client = _FakeClient("  olá do áudio  ")
    stt = GeminiBatchTranscriber(None, client=client)
    text = asyncio.run(stt.transcribe(b"RIFF...", "audio/wav"))

    assert text == "olá do áudio"
    kwargs = client.aio.models.kwargs
    assert kwargs["contents"][0].inline_data.mime_type == "audio/wav"
    assert isinstance(kwargs["contents"][1], str)


# -- TTS -------------------------------------------------------------------

def test_tts_config_usa_audio_e_voz_pre_construida():
    tts = GeminiTTS("chave-falsa", voice="Puck")
    config = tts.build_config()
    assert isinstance(config, types.GenerateContentConfig)
    assert list(config.response_modalities) == ["AUDIO"]
    assert config.speech_config.voice_config.prebuilt_voice_config.voice_name == "Puck"


def test_parse_mime_rate_nao_adivinha():
    assert parse_mime_rate("audio/L16;codec=pcm;rate=24000") == 24000
    assert parse_mime_rate("audio/L16;codec=pcm;rate=16000") == 16000
    assert parse_mime_rate(None) == SPEAKER_SAMPLE_RATE
    assert parse_mime_rate("audio/pcm") == SPEAKER_SAMPLE_RATE


def test_extract_audio_le_inline_data_e_taxa():
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                data=b"\x01\x02\x03\x04",
                                mime_type="audio/L16;rate=24000",
                            )
                        )
                    ]
                )
            )
        ]
    )
    pcm, rate = extract_audio(response)
    assert pcm == b"\x01\x02\x03\x04"
    assert rate == 24000


def test_extract_audio_sem_audio():
    from google.genai import types as t

    response = t.GenerateContentResponse(
        candidates=[t.Candidate(content=t.Content(parts=[t.Part(text="sem áudio")]))]
    )
    assert extract_audio(response) == (b"", SPEAKER_SAMPLE_RATE)


class _FakePlayer:
    def __init__(self): self.played = []
    async def play(self, pcm, sample_rate):
        self.played.append((pcm, sample_rate))


class _TTSResponseClient:
    """Cliente fake cujo generate_content devolve um blob de áudio real."""

    class _Models:
        async def generate_content(self, **kwargs):
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[
                                types.Part(
                                    inline_data=types.Blob(
                                        data=b"\x00\x01\x02\x03",
                                        mime_type="audio/L16;rate=22050",
                                    )
                                )
                            ]
                        )
                    )
                ]
            )

    def __init__(self):
        self.aio = type("Aio", (), {"models": self._Models()})()


def test_gemini_tts_speak_reproduz_pcm_na_taxa_da_resposta():
    import asyncio

    player = _FakePlayer()
    tts = GeminiTTS(None, player=player, client=_TTSResponseClient())
    asyncio.run(tts.speak("olá"))
    assert player.played == [(b"\x00\x01\x02\x03", 22050)]


def test_gemini_tts_texto_vazio_nao_chama_api():
    import asyncio

    player = _FakePlayer()
    tts = GeminiTTS(None, player=player, client=_TTSResponseClient())
    asyncio.run(tts.speak("   "))
    assert player.played == []


def test_null_speaker_registra_sem_audio():
    import asyncio

    speaker = NullSpeaker()
    asyncio.run(speaker.speak("texto"))
    assert speaker.spoken == ["texto"]


def test_system_speaker_comando_linux_le_texto_do_stdin():
    speaker = SystemSpeaker()
    command, stdin, env = speaker._command("olá, mundo")
    assert command[0] == "spd-say" or command[0] == "say" or command[0] == "powershell"
    if command[0] == "spd-say":
        assert stdin == "olá, mundo\n".encode("utf-8")
        assert env is None


# -- áudio -----------------------------------------------------------------

def test_wav_bytes_e_um_wav_valido():
    import io
    import wave

    pcm = b"\x00\x01" * 160
    data = wav_bytes(pcm, 16000)
    with wave.open(io.BytesIO(data), "rb") as wav:
        assert wav.getframerate() == 16000
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.readframes(160) == pcm


def test_deteccao_de_backends_nao_inventa():
    mic = detect_microphone_command()
    player = detect_player_command(24000)
    caps = audio_capabilities()
    assert caps["sample_rate_in"] == MIC_SAMPLE_RATE
    assert caps["sample_rate_out"] == SPEAKER_SAMPLE_RATE
    if mic is not None:
        assert mic[0] in ("parec", "arecord")
    if player is not None:
        assert player[0] in ("aplay", "paplay")
    assert set(caps["tools_available"]) >= {"parec", "arecord", "aplay", "paplay"}
