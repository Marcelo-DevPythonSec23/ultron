# DEVELOPMENT_STATE — estado técnico real

**Data:** 2026-11-10
**Regra:** toda linha tem evidência (arquivo/teste). Planejamento não é
implementação. Classificações: `IMPLEMENTED`, `PARTIAL`, `PLANNED`, `BLOCKED`,
`DEPRECATED`, `UNKNOWN`.

## 1. Módulos existentes (código)

```text
ultron-2.0/ultron_2_0/
├── bootstrap.py            # raízes, .env absoluto, banco isolado
├── core_runtime.py         # wiring do núcleo lain + loop dedicado
├── orchestrator_bridge.py  # entrada única (CLI/voz/HUD)
├── cli.py                  # interface de texto
├── tool_contracts.py       # ToolContract / ToolResult
├── tool_gateway.py         # allowlist/validação/timeout/confirmação/auditoria
├── tool_loop.py            # ToolCallingProvider (protocolo JSON)
├── marklvi_actions.py      # subset curado de actions do Mark-LVI
├── memory_tools.py         # FactMemory + remember/recall/forget
├── memory_engine.py        # tipos/escopo/versão/retenção/consolidação
├── memory_injection.py     # memória recuperada no prompt (por turno)
├── voice/                  # audio_io, contracts, stt_gemini, tts, pipeline, runner
└── web/                    # app FastAPI, server uvicorn, static/index.html
```

## 2. Funcionalidades

| # | Funcionalidade | Estado | Evidência |
|---|---|---|---|
| 1 | Inicialização do núcleo por composição | `IMPLEMENTED` | `core_runtime.start`, `test_core_runtime.py` |
| 2 | Conversa por texto no orquestrador do lain | `IMPLEMENTED` | `cli.py`, `test_bridge.py` |
| 3 | Histórico único persistente | `IMPLEMENTED` | `ChatService`, `test_bridge.py` |
| 4 | Providers mock/gemini no Registry do lain | `IMPLEMENTED` | `core_runtime.py`, validação ao vivo |
| 5 | Tool calling (protocolo JSON, até 4 rodadas) | `IMPLEMENTED` | `tool_loop.py`, `test_tool_loop.py` (9) |
| 6 | Gateway: allowlist/validação/tipos/desconhecidos | `IMPLEMENTED` | `tool_gateway.py`, `test_tool_gateway.py` (11) |
| 7 | Timeout e execução em thread | `IMPLEMENTED` | `tool_gateway.py`, `test_faults.py` |
| 8 | Confirmação de ação sensível | `PARTIAL` | campo existe; sem UI → recusa (`forget`) |
| 9 | Ferramenta `system_status` (métricas reais) | `IMPLEMENTED` | `test_integration_tools.py` |
| 10 | `open_app` | `IMPLEMENTED` (valida allowlist) | `marklvi_actions.py` |
| 11 | `web_search` (DuckDuckGo) | `IMPLEMENTED` (rede) | `marklvi_actions.py` |
| 12 | `reminder` | `IMPLEMENTED` (processo local) | `marklvi_actions.py` |
| 13 | `remember`/`recall` textual | `IMPLEMENTED` | `memory_tools.py`, `test_memory_tools.py` |
| 14 | `forget` | `PARTIAL` (sem UI de confirmação) | `test_gateway_bloqueia_forget...` |
| 15 | Memória tipada/versionada/consolidação | `IMPLEMENTED` | `memory_engine.py`, `test_memory_engine.py` (17), `docs/memory/` |
| 15a | Injeção de memória no prompt (1×/turno) | `IMPLEMENTED` | `memory_injection.py`, `test_memory_engine.py` |
| 15b | Busca semântica (embeddings) | `PLANNED` | não há provedor/dependência |
| 16 | STT Gemini Live (só transcrição) | `IMPLEMENTED` | `stt_gemini.py`, `test_voice_units.py` |
| 17 | STT em lote (arquivo) | `IMPLEMENTED` | `GeminiBatchTranscriber` |
| 18 | TTS Gemini | `IMPLEMENTED` + validado ao vivo | `tts.py`, `docs/TESTING.md` |
| 19 | TTS do sistema (`spd-say`/`say`/SAPI) | `IMPLEMENTED` | `SystemSpeaker` |
| 20 | Reprodução PCM (`aplay`/`paplay`) | `IMPLEMENTED` | `audio_io.py` |
| 21 | Voz reusando o mesmo núcleo | `IMPLEMENTED` | `voice/pipeline.py`, `test_voice_pipeline.py` |
| 22 | Falha de TTS preserva texto | `IMPLEMENTED` | `test_faults.py` |
| 23 | HUD web (estado/chat/histórico/tools) | `IMPLEMENTED` | `web/app.py`, `test_web.py` (11) |
| 24 | Recuperação de falhas (provedor/dispositivo/conexão/tool/TTS) | `IMPLEMENTED` | `test_faults.py` (10) |
| 25 | Wake word / VAD / barge-in | `PLANNED` | não há código |
| 26 | Model Router | `PLANNED` | não implementar fictício |
| 27 | MCP / agentes externos | `PLANNED` | — |
| 28 | Actions de escrita/execução do Mark-LVI | `BLOCKED` | risco; ver `INTEGRATION_MAP.md` |
| 29 | API HTTP do lain (`app/api`) | `DEPRECATED` no 2.0 | HUD próprio substitui |

## 3. Testes existentes

| Arquivo | Testes | Cobre |
|---|---|---|
| `test_bootstrap.py` | 6 | caminhos, `.env`, banco isolado |
| `test_core_runtime.py` | 5 | wiring, providers, ciclo de vida |
| `test_bridge.py` | 5 | conversa única, status, demo, one-shot |
| `test_tool_gateway.py` | 11 | validação e segurança |
| `test_tool_loop.py` | 9 | protocolo, rodadas, streaming |
| `test_integration_tools.py` | 2 | tool real, subset |
| `test_memory_tools.py` | 8 | memória explícita |
| `test_memory_engine.py` | 17 | motor tipado, escopo, versão, exclusão, injeção, tools |
| `test_voice_units.py` | 15 | STT/TTS/áudio |
| `test_voice_pipeline.py` | 6 | fluxo de voz |
| `test_faults.py` | 10 | Teste G |
| `test_web.py` | 11 | HUD |
| `test_docs.py` | 4 | caminhos/índice documental |
| **Total** | **109** | |

Regressão do núcleo: **64** testes em `lain/`.

## 4. Problemas conhecidos

1. `forget` não pode ser confirmado pela interface → sempre recusado (seguro).
2. `browser_control`/`screen_processor` do Mark-LVI falham ao importar sem
   `playwright`/`numpy` — por isso ficam fora do subset.
3. Sem teste ao vivo automatizado de STT Live (rede/microfone).
4. `Mark-LVI-main` não é repo git.
5. Captura automática de memória **não existe por decisão** (só `remember`).
6. Consolidação e expiração são operações de API, sem agendador no runtime.
7. Busca semântica (embeddings) não implementada; recuperação é lexical.
8. Memória em JSON sem criptografia/backup automático (risco registrado).

## 5. Dependências

`fastapi`, `sqlalchemy`, `aiosqlite`, `pydantic`, `pydantic-settings`,
`python-dotenv`, `google-genai>=3,<4`, `psutil`, `ddgs`, `uvicorn`.
Dev: `pytest`, `pytest-asyncio`.

## 6. Próximos objetivos (priorizados)

1. Interface de confirmação para `forget` e ações sensíveis.
2. Expor escopo/tags/trust, episódios e procedimentos nas tools/HUD.
3. Busca semântica opcional (embeddings) sem virar dependência obrigatória.
4. Agendador de `expire()`/`consolidate()` e métricas de qualidade.
5. Criptografia em repouso e backup/restauração de `data/`.
6. Retry/backoff padronizado para providers.
