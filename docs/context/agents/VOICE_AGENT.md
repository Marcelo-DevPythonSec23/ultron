# VOICE_AGENT — contexto do agente de voz

## Responsabilidade
Manter captura, STT, TTS e reprodução funcionando como **interface** do núcleo,
sem criar um segundo ciclo conversacional.

## Partes relevantes
`ultron_2_0/voice/` (`audio_io`, `stt_gemini`, `tts`, `pipeline`, `runner`),
`orchestrator_bridge.py`; `Mark-LVI-main/main.py` (referência do Live, não
executado), `Mark-LVI-main/providers/` (referência, não instalado).

## Documentos obrigatórios
1. `docs/VOICE_PIPELINE.md`
2. `docs/context/KNOWN_LIMITATIONS.md`
3. `docs/SECURITY.md`
4. `docs/TESTING.md`
5. `docs/context/TECHNICAL_DECISIONS.md` (ADR-005, ADR-008)

## Interfaces que deve respeitar
- STT entrega texto a `OrchestratorBridge.process_text` (mesmo caminho do texto).
- Live só transcreve (`response_modalities=["TEXT"]`, sem tools).
- TTS recebe o texto da resposta; falha de TTS não derruba o turno.
- Áudio: PCM 16-bit mono; taxas reais do mime_type (nunca adivinhar).

## Restrições
- `google-genai` 3.0.0: TTS **exige** `api_version="v1beta"`.
- Não abrir microfone sem pedido explícito do usuário.
- Não implementar wake word/VAD/barge-in fictícios.
- Não bloquear o event loop em operações de áudio.

## Testes que deve executar
`test_voice_units.py` (15), `test_voice_pipeline.py` (6),
`test_faults.py` (10). Validação ao vivo quando houver chave/rede/microfone.

## Critérios de conclusão
- Um único histórico comprovado.
- Falhas de dispositivo/conexão tratadas.
- TTS validado (ao vivo quando possível).
- Documentação reflete o comportamento real.

## Coordenação
Com BACKEND (bridge) e QA (fluxo completo). Não alterar o núcleo para
acomodar áudio.
