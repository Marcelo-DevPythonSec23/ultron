# TESTING — testes, resultados e limitações

## 1. Como executar

```bash
# suíte do ULTRON 2.0 (231 testes)
cd ultron-2.0
./.venv/bin/python -m pytest -q

# regressão do núcleo original (64 testes, projeto não modificado)
cd ../lain
./.venv/bin/python -m pytest -q
```

O `pytest` do 2.0 usa `asyncio_mode="auto"`, banco `sqlite+aiosqlite:///:memory:`
na maioria dos testes e um provedor scriptável (`tests/fakes.py`) que implementa
o contrato real `LLMProvider` — não é mock de unidade: exercita o orquestrador,
o proxy de ferramentas e a persistência reais sem rede.

## 2. Cobertura por arquivo (177 testes)

| Arquivo | Testes | O que valida |
|---|---|---|
| `tests/test_bootstrap.py` | 6 | raízes absolutas, `sys.path` idempotente, banco isolado, `.env` do lain sem CWD |
| `tests/test_core_runtime.py` | 5 | wiring do núcleo, providers, ciclo de vida, banco em memória |
| `tests/test_bridge.py` | 5 | conversa única pela interface, `/status`, CLI `--demo`, one-shot, banco próprio |
| `tests/test_tool_gateway.py` | 11 | allowlist, obrigatórios, tipos/coerção, parâmetros desconhecidos, timeout, confirmação, exceções |
| `tests/test_tool_loop.py` | 9 | protocolo JSON, resultado como dado, teto de rodadas, streaming único, provider sem tools |
| `tests/test_integration_tools.py` | 4 | `system_status` real; subset registrado; `forget` real só após aprovação e nada apagado na recusa |
| `tests/test_authorization.py` | 14 | token de uso único, replay, expiração, argumentos alterados, concorrência, integração com o gateway |
| `tests/test_memory_tools.py` | 8 | `remember`/`recall`/`forget`, categorias, recusa de `forget`, nada automático, `long_term.json` intocado |
| `tests/test_memory_engine.py` | 17 | tipos, escopo, dedupe, versão, exclusão autorizada, consolidação, orçamento, expiração, injeção no prompt, tools pelo motor |
| `tests/test_docs.py` | 5 | caminhos obrigatórios, índice sem fantasmas, links internos, ponteiro de contexto |
| `tests/test_voice_units.py` | 14 | contratos, PCM/WAV, comandos de dispositivo, mime/rate, extração de áudio, `SystemSpeaker`, falhas |
| `tests/test_voice_pipeline.py` | 6 | transcript → núcleo, `handle_audio`, TTS opcional, mesmo `conversation_id`, turno vazio |
| `tests/test_faults.py` | 10 | Teste G: provedor, microfone, subprocesso, player, STT, parâmetro, tool inexistente, TTS, fluxo voz→tool→voz |
| `tests/test_web.py` | 21 | HUD: HTML/tokens, acessibilidade/movimento reduzido, status real, tools, chat + histórico, `/api/new`, 502, entrada inválida, bind local, aprovação/recusa/replay; métricas reais (`/api/system` + 503), atividade da sessão (`/api/activity`), `busy` |
| `tests/test_routing.py` | 41 | Model Router (Fase 3): inferência de tarefa, catálogo/capacidades, política de seleção, retry com backoff, métricas/cooldown/sanitização, fallback entre provedores, isolamento de falhas, provedor/modelo explícitos, mock nunca como fallback, streaming com failover antes do 1º chunk, configuração por env sem segredos, modo `auto` (seleção por tipo de tarefa + sentinela `"auto"`), integração real pelo bridge |
| `tests/test_agents.py` | 19 | Sistema Multiagente (Fase 4): registro/descoberta de agentes, ciclo de vida (pending→completed/failed), execução com resultado estruturado, validação (dados não confiáveis), falha e replanejamento com tentativas, concorrência com isolamento de arquivos, agente não encontrado sem quebrar o orquestrador, status sem credenciais, integração com core_runtime e bridge |
| `tests/test_integrations.py` | 19 | Integrações externas (Fase 5): build_command OpenCode (comando real), parse de saída JSON e texto bruto, sanitização de segredos (AIza, sk-), integração desabilitada não executa, comando não encontrado tratado, timeout tratado, IntegrationRegistry (registro/listar/habilitar/desabilitar), IntegrationOrchestrator (criar tarefa, executar, não registrada, desabilitada), status sem credenciais, integração com core_runtime e bridge |
| `tests/test_memory_phase6.py` | 16 | Evolução da Memória (Fase 6): compatibilidade memória existente, índice semântico opcional (fallback sem embeddings), busca semântica/híbrida, backup/restauração round-trip, criptografia opcional (sem dependência), generate_key_file |

## 3. Mapa com os testes do AGENTS.md

| Teste | Onde é coberto | Evidência |
|---|---|---|
| **A — Inicialização** | `test_bootstrap`, `test_core_runtime`, `test_bridge`, `test_web` | núcleo sobe, settings/providers carregam, banco isolado criado, sem import circular |
| **B — Conversação por texto** | `test_bridge`, `test_web` | mensagem → orquestrador → provider → resposta → persistência |
| **C — STT** | `test_voice_units`, `test_voice_pipeline`, `test_faults` | comandos reais de microfone, transcrição em lote, queda de conexão, microfone ausente |
| **D — TTS** | `test_voice_units`, `test_voice_pipeline`, `test_faults` | síntese/reprodução, falha de player, recuperação no turno seguinte |
| **E — Ferramentas** | `test_tool_gateway`, `test_tool_loop`, `test_integration_tools`, `test_authorization` | descoberta/contrato/validação/autorização/execução/interpretação |
| **F — Fluxo completo** | `test_faults::test_fluxo_completo_voz_tool_voz...` | fala → núcleo → tool real → texto → TTS, **uma** conversa |
| **Fase 3 — Model Router** | `tests/test_routing.py` (41) | seleção por tarefa, fallback, retry, timeout, modo `auto`, integração bridge, sem vazamento de segredo |
| **Fase 4 — Multiagente** | `tests/test_agents.py` (19) | registro/descoberta, ciclo de vida, execução, validação, falha/replanejamento, concorrência/isolamento de arquivos, integração runtime/bridge |
| **Fase 5 — CLI/MCP** | `tests/test_integrations.py` (19) | build_command real, parse de saída, sanitização de segredos, integração desabilitada, comando não encontrado, timeout, registro/habilitar/desabilitar, orquestrador, integração runtime/bridge |
| **Fase 6 — Evolução da Memória** | `tests/test_memory_phase6.py` (16) | compatibilidade memória existente, índice semântico opcional (fallback sem embeddings), busca semântica/híbrida, backup/restauração round-trip, criptografia opcional (sem dependência), generate_key_file |
| **G — Falhas controladas** | `test_faults` (10) | provedor, dispositivo, subprocesso, conexão, parâmetro, timeout, tool inexistente, TTS |

## 4. Resultados registrados

| Data | Suíte | Resultado |
|---|---|---|
| 2026-11-10 | ULTRON 2.0 (`ultron-2.0/.venv`) | **109 passed** (baseline da integração 0–10) |
| 2026-11-11 | ULTRON 2.0 após a Fase 2 | **128 passed** |
| 2026-11-11 | ULTRON 2.0 após a Fase 2.5 | **136 passed** |
| 2026-11-11 | ULTRON 2.0 após a Fase 3 (Model Router) | **177 passed** |
| 2026-11-11 | ULTRON 2.0 após a Fase 4 (Multiagente) | **196 passed** |
| 2026-11-11 | ULTRON 2.0 após a Fase 5 (CLI/MCP) | **215 passed** |
| 2026-11-11 | ULTRON 2.0 após a Fase 6 (Evolução da Memória) | **231 passed** |
| 2026-11-11 | Regressão lain (após a Fase 2) | **64 passed** |
| 2026-11-10 | Memória (`tests/test_memory_engine.py`) | **17 passed** |
| 2026-11-10 | Regressão lain (`lain/.venv`) | **64 passed** |
| 2026-11-10 | Smoke HTTP do HUD (`127.0.0.1:8799`) | `/` 200 (14 522 bytes), `/api/status`, `/api/tools`, `/api/chat`, `/api/history` reais |
| 2026-11-10 | `python -m ultron_2_0.voice --list-devices` | `parec` + `aplay` detectados; taxas 16 kHz/24 kHz |

## 5. Integridade dos projetos originais

Verificações executadas:

- `lain/ultron.db` com **12 conversas / 48 mensagens**, inalterado;
- `Mark-LVI-main/memory/long_term.json` com mtime inalterado (teste dedicado);
- `Mark-LVI-main/config/api_keys.json` inexistente e não criado;
- nenhum arquivo de `lain/` ou `Mark-LVI-main/` alterado pelo 2.0;
- banco padrão do 2.0 sempre em `ultron-2.0/data/ultron2.db` (teste de bootstrap).

## 6. Limitações dos testes (honestas)

O que a suíte **não** cobre:

- chamadas reais ao Gemini (texto, Live/*STT* e TTS) — exigiriam rede/quota; os
  testes usam provedores scriptáveis e exercitam apenas os caminhos de código;
- execução real de `open_app`, `web_search` e `reminder` — efeitos externos;
  apenas `system_status` é executado de verdade (não destrutivo);
- microfone/alto-falante físicos — o ambiente tem `parec`/`aplay`, mas os testes
  usam subprocessos controlados;
- wake word, VAD e barge-in — não implementados, portanto não testados;
- aprovação interativa: coberta com handler/threads e HTTP (sem TTY real nem navegador); a recusa por voz é validada como política, sem áudio real;
- busca semântica/embeddings — não implementados, portanto não testados;
- memória: dois processos concorrentes no mesmo arquivo, corrupção de escrita
  induzida e qualidade de recuperação (precisão/recall) não são medidos; a
  injeção usa provedor scriptável, sem chamada real ao Gemini;
- carga/concorrência e uso prolongado de memória — não medidos;
- HUD em navegador real — validado por HTTP e pelo conteúdo do HTML, não por
  teste de UI automatizado.

Nenhuma dessas lacunas é apresentada como funcionalidade concluída.
