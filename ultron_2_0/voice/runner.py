"""CLI de voz do ULTRON 2.0 (`python -m ultron_2_0.voice`).

Modos:

  * ao vivo (padrão): microfone -> Gemini Live (transcrição) -> núcleo ULTRON
    -> texto impresso + TTS;
  * `--audio ARQUIVO`: STT em lote de um WAV e um único turno (útil para
    validação sem microfone);
  * `--list-devices`: mostra o que esta máquina realmente oferece.

O núcleo e o banco são os mesmos da CLI de texto; a chave lida é a do `.env`
do lain, via Settings do runtime — nunca é impressa.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from ..orchestrator_bridge import OrchestratorBridge
from .audio_io import (
    AudioUnavailableError,
    SubprocessMicrophone,
    SubprocessPlayer,
    audio_capabilities,
)
from .pipeline import VoicePipeline
from .stt_gemini import BATCH_MODEL_DEFAULT, GeminiBatchTranscriber, GeminiLiveSTT, LIVE_MODEL_DEFAULT
from .tts import TTS_MODEL_DEFAULT, TTS_VOICE_DEFAULT, GeminiTTS, SystemSpeaker

logger = logging.getLogger("ultron2.voice")


def _build_speaker(args, api_key: str | None):
    if args.no_tts:
        return None
    if api_key:
        try:
            return GeminiTTS(api_key, model=args.tts_model, voice=args.voice)
        except ValueError:
            pass
    if SystemSpeaker.available():
        return SystemSpeaker(language=args.language)
    raise AudioUnavailableError(
        "sem TTS disponível: configure GEMINI_API_KEY ou instale `spd-say`"
    )


def _print_turn(turn) -> None:
    print(f"\nvocê> {turn.transcript}")
    print(f"ultron> {turn.response_text}")
    detail = []
    if turn.provider:
        detail.append(turn.provider)
    if turn.model:
        detail.append(turn.model)
    if turn.spoken:
        detail.append("voz")
    elif turn.tts_error:
        detail.append(f"texto (TTS falhou: {turn.tts_error})")
    if detail:
        print(f"  [{' | '.join(detail)}]")


async def _run_file(args, bridge: OrchestratorBridge, api_key: str | None) -> int:
    transcriber = GeminiBatchTranscriber(api_key, model=args.stt_model)
    speaker = _build_speaker(args, api_key)
    pipeline = VoicePipeline(bridge, speaker=speaker, transcriber=transcriber)
    path = Path(args.audio)
    data = path.read_bytes()
    mime = "audio/wav" if path.suffix.lower() == ".wav" else "audio/ogg"
    turn = await pipeline.handle_audio(data, mime)
    _print_turn(turn)
    return 0 if turn.ok else 1


async def _run_live(args, bridge: OrchestratorBridge, api_key: str | None) -> int:
    microphone = SubprocessMicrophone()
    transcriber = GeminiLiveSTT(
        api_key, model=args.live_model, language_code=args.language
    )
    speaker = _build_speaker(args, api_key)
    pipeline = VoicePipeline(
        bridge,
        speaker=speaker,
        on_transcript=lambda text: print(f"\n  (transcrito: {text})"),
    )

    stop = asyncio.Event()

    async with transcriber.connect() as live:

        async def pump_microphone() -> None:
            async for chunk in microphone.chunks():
                if stop.is_set():
                    return
                await live.send_audio(chunk)

        async def pump_transcripts() -> None:
            async for text in live.transcripts():
                if stop.is_set():
                    return
                turn = await pipeline.handle_transcript(text)
                _print_turn(turn)

        async def timer() -> None:
            await asyncio.sleep(args.duration)
            stop.set()

        tasks = [
            asyncio.create_task(pump_microphone(), name="mic"),
            asyncio.create_task(pump_transcripts(), name="stt"),
        ]
        if args.duration and args.duration > 0:
            tasks.append(asyncio.create_task(timer(), name="timer"))

        try:
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            stop.set()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    for task in done:
        if task.cancelled():
            continue
        exc = task.exception()
        if exc is not None:
            raise exc
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ultron2.voice",
        description="ULTRON 2.0 — voz (STT Gemini Live -> núcleo ULTRON -> TTS)",
    )
    parser.add_argument("--provider", default=None, help="provedor do núcleo (mock, gemini...)")
    parser.add_argument("--database", default=None, help="banco do 2.0 (padrão: data/ultron2.db)")
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--audio", default=None, help="transcreve um arquivo e executa um turno")
    parser.add_argument("--list-devices", action="store_true", help="diagnóstico de áudio e sai")
    parser.add_argument("--no-tts", action="store_true", help="não fala a resposta (texto sempre sai)")
    parser.add_argument("--language", default=None, help="código de idioma (ex.: pt-BR)")
    parser.add_argument("--live-model", default=LIVE_MODEL_DEFAULT)
    parser.add_argument("--stt-model", default=BATCH_MODEL_DEFAULT)
    parser.add_argument("--tts-model", default=TTS_MODEL_DEFAULT)
    parser.add_argument("--voice", default=TTS_VOICE_DEFAULT)
    parser.add_argument("--duration", type=float, default=0, help="encerra após N segundos (0 = até Ctrl+C)")
    parser.add_argument("--verbose", action="store_true")
    return parser


def _deny_sensitive_action(action) -> bool:
    """Voz NÃO autoriza ações sensíveis (AGENTS.md 2.1, Fase 2).

    Não existe autenticação confiável por voz; aprovar por áudio permitiria que
    qualquer pessoa no ambiente liberasse uma exclusão. A recusa é explícita e
    o núcleo informa o usuário para confirmar pela CLI/HUD.
    """
    print(
        f"\n  [voz] '{action.tool_name}' exige confirmação; autorização por voz "
        "não é suportada — confirme pela CLI ou pelo HUD.\n"
    )
    return False


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.list_devices:
        caps = audio_capabilities()
        print("ULTRON 2.0 — dispositivos de áudio")
        print(f"  microfone : {caps['microphone'] or '(indisponível)'}")
        print(f"  alto-falante: {caps['speaker'] or '(indisponível)'}")
        print(f"  entrada   : {caps['sample_rate_in']} Hz | saída: {caps['sample_rate_out']} Hz")
        print(f"  ferramentas: {caps['tools_available']}")
        return 0 if caps["microphone"] else 2

    bridge = OrchestratorBridge(
        project_root=args.project_root,
        database_url=args.database,
        default_provider=args.provider,
        confirmation_handler=_deny_sensitive_action,
    )
    bridge.start()
    try:
        api_key = bridge.runtime.settings.get_gemini_api_key()
        if args.audio:
            return asyncio.run(_run_file(args, bridge, api_key))
        return asyncio.run(_run_live(args, bridge, api_key))
    except AudioUnavailableError as exc:
        print(f"\n[áudio indisponível] {exc}\n", file=sys.stderr)
        print("  diagnóstico: python -m ultron_2_0.voice --list-devices", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n[encerrado]")
        return 0
    except Exception as exc:  # falha controlada: a voz não derruba o núcleo
        logger.exception("falha na camada de voz")
        print(f"\n[falha de voz] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("  o núcleo e o histórico continuam intactos.", file=sys.stderr)
        return 3
    finally:
        bridge.stop()


if __name__ == "__main__":
    raise SystemExit(main())
