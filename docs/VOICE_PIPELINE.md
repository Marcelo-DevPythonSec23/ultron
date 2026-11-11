# VOICE_PIPELINE — captura, STT, processamento, TTS e reprodução

A voz no ULTRON 2.0 é **interface**, não um segundo cérebro. O STT entrega
texto ao MESMO `OrchestratorBridge.process_text` usado pela CLI e pelo HUD; o
`Orchestrator` do lain continua sendo o único ciclo de conversa e o único
histórico. Nada do ciclo de sessão do `Mark-LVI-main/main.py` é executado.

## 1. Fluxo implementado

```text
Microfone (parec ou arecord)                      [audio_io.SubprocessMicrophone]
   │  PCM 16-bit mono @ 16 kHz, chunks de ~100 ms
   ▼
Gemini Live — SOMENTE transcrição                 [stt_gemini.GeminiLiveSTT]
   │  LiveConnectConfig(response_modalities=["TEXT"],
   │                    input_audio_transcription=...)
   │  transcript final por turno de fala
   ▼
VoicePipeline.handle_transcript                   [voice/pipeline.py]
   │
   ▼
OrchestratorBridge.process_text                   ← MESMO caminho da CLI
   │
   ▼
Orchestrator do lain (contexto, memória, persistência)
   │
   ├── texto da resposta (SEMPRE impresso/devolvido)
   └── TTS opcional
         ├── GeminiTTS (generate_content, response_modalities=["AUDIO"])
         │     → PCM 16-bit na taxa real do mime_type → aplay/paplay
         └── SystemSpeaker (spd-say/say/SAPI) quando não há chave/API
```

Falha de TTS **não** derruba o turno: `VoiceTurn.response_text` continua
preenchido e `tts_error` registra o motivo. Falha de microfone, de conexão Live
ou de player gera erro explícito e código de saída controlado.

## 2. Componentes e contratos

| Componente | Arquivo | Contrato real |
|---|---|---|
| `SubprocessMicrophone` | `voice/audio_io.py` | `chunks() -> AsyncIterator[bytes]`; encerra o subprocesso no `finally` |
| `SubprocessPlayer` | `voice/audio_io.py` | `play(pcm, rate)`; erro se o player sair com código ≠ 0 |
| `GeminiLiveSTT` | `voice/stt_gemini.py` | `connect()` → sessão; `transcripts()` entrega falas finais |
| `GeminiBatchTranscriber` | `voice/stt_gemini.py` | `transcribe(audio, mime_type)` — usado por `--audio` |
| `GeminiTTS` | `voice/tts.py` | `speak(text)`; `synthesize(text) -> (pcm, rate)` |
| `SystemSpeaker` | `voice/tts.py` | `speak(text)` via `spd-say --pipe-mode` (Linux), `say` (macOS), PowerShell/SAPI (Windows) |
| `NullSpeaker` | `voice/tts.py` | registra textos em testes/CI, sem áudio |
| `VoicePipeline` | `voice/pipeline.py` | `handle_transcript` / `handle_audio` → `VoiceTurn` |
| `VoiceTurn` | `voice/contracts.py` | transcript, response_text, spoken, tts_error, ids, provider/model |

Taxas fixas (as mesmas do Mark-LVI): entrada 16 000 Hz, saída padrão
24 000 Hz (a taxa efetiva do Gemini TTS vem do `mime_type`, nunca é adivinhada).

## 3. Uso real

```bash
cd ultron-2.0
./.venv/bin/python -m ultron_2_0.voice --list-devices     # diagnóstico do ambiente
./.venv/bin/python -m ultron_2_0.voice                    # microfone + STT + TTS
./.venv/bin/python -m ultron_2_0.voice --no-tts           # fala e lê a resposta
./.venv/bin/python -m ultron_2_0.voice --audio fala.wav --no-tts
./.venv/bin/python -m ultron_2_0 --voice                  # atalho pela CLI principal
```

Opções relevantes: `--provider`, `--database`, `--language pt-BR`,
`--live-model`, `--stt-model`, `--tts-model`, `--voice`, `--duration N`.

Sem `GEMINI_API_KEY`, o STT não inicia (erro explícito). O TTS cai para a voz do
sistema se `spd-say` estiver disponível; `--no-tts` mantém a conversa
inteiramente textual.

## 4. Ciclos de vida independentes

- Microfone e player são subprocessos separados, criados e encerrados por turno
  de captura/reprodução; não há dispositivo mantido aberto sem uso.
- O núcleo roda no loop dedicado do `UltronCoreRuntime`; `process_text` é
  chamado via `asyncio.to_thread` para não bloquear o loop da voz.
- `Ctrl+C` encerra as tarefas pendentes (`stop` event + `cancel`) e para o
  subprocesso do microfone no `finally`.
- Nenhuma thread de áudio toca no núcleo diretamente.

## 5. Limitações atuais (não são simulações)

| Item | Estado |
|---|---|
| Wake word | **não integrado** — `openwakeword` não instalado; nenhum fallback falso |
| VAD | **não integrado** — o corte de turno vem da transcrição do Live (`finished`/`turn_complete`) |
| Barge-in / interrupção da fala do ULTRON | **não implementado** |
| Seleção de dispositivo de entrada/saída | usa o dispositivo padrão do sistema |
| Streaming de texto durante o turno | não usado; a resposta final é um único texto |
| Confirmação por voz de ações destrutivas | não implementada; o gateway recusa `forget` |

O microfone depende de `parec` (PulseAudio/PipeWire) ou `arecord` (ALSA); a
reprodução depende de `aplay` ou `paplay`. `--list-devices` reporta exatamente o
que a máquina oferece, sem inventar suporte.
