# MODULE_MAP — mapa dos módulos reais

Cada entrada aponta o arquivo real, a responsabilidade concreta e os testes.
Se não houver evidência, o estado é `UNKNOWN`.

## 1. Núcleo de integração (`ultron-2.0/ultron_2_0/`)

### `bootstrap.py`
- **Responsabilidade:** resolver raízes absolutas (`PROJECT_ROOT`, `LAIN_ROOT`,
  `MARKLVI_ROOT`), inserir `lain/` e `Mark-LVI-main/` no `sys.path`, construir
  `Settings` com `.env` do lain por caminho absoluto e URL de banco isolada.
- **Entrada:** `project_root` opcional / `ULTRON2_PROJECT_ROOT`.
- **Saída:** tupla de paths; `Settings`; URL `sqlite+aiosqlite:///…/data/ultron2.db`.
- **Estado:** `IMPLEMENTED`. **Testes:** `test_bootstrap.py`.

### `core_runtime.py`
- **Responsabilidade:** montar o núcleo original do lain por composição
  (`Settings`, engine, repositórios, `ChatService`, `ContextManager`,
  `PromptEngine`, `ProviderRegistry`, `Orchestrator`), registrar providers
  (mock/gemini) e envolvê-los com `MemoryInjectionProvider` (por fora) e
  `ToolCallingProvider` (por dentro); criar o `MemoryEngine` sempre; gerenciar
  event loop dedicado (`start_background`/`run_coro`/`stop_background`).
- **Saída:** `runtime.chat()` (async), `chat_sync()`, `runtime.memory_engine`,
  `runtime.memory` (`engine.facts`).
- **Estado:** `IMPLEMENTED`. **Testes:** `test_core_runtime.py`, `test_faults.py`,
  `test_memory_engine.py`.

### `orchestrator_bridge.py`
- **Responsabilidade:** ponta de entrada única para interfaces; mantém o
  `conversation_id` da sessão; expõe `process_text`, `history`, `status`.
- **Estado:** `IMPLEMENTED`. **Testes:** `test_bridge.py`, `test_web.py`.

### `cli.py`
- **Responsabilidade:** REPL/one-shot/demo; comandos `/status`, `/tools`,
  `/new`, `/quit`; `--voice` delega ao runner de voz.
- **Estado:** `IMPLEMENTED`. **Testes:** `test_bridge.py`.

### `tool_contracts.py`
- **Responsabilidade:** `ToolContract` (nome, descrição, schema, obrigatórios,
  timeout, confirmação, `authorization_timeout_seconds`, permissões, fonte,
  erros) e `ToolResult`.
- **Estado:** `IMPLEMENTED`. **Testes:** `test_tool_gateway.py`.

### `authorization.py`
- **Responsabilidade:** `AuthorizationManager`, `PendingAction` e token de uso
  único; expiração, vínculo ferramenta+argumentos (fingerprint), proteção contra
  replay, concorrência (`Lock` + `Event`) e auditoria.
- **Estado:** `IMPLEMENTED`. **Testes:** `test_authorization.py` (14).

### `tool_gateway.py`
- **Responsabilidade:** allowlist, validação de parâmetros/tipos, rejeição de
  desconhecidos, autorização interativa (`_authorize`), timeout em thread,
  auditoria.
- **Estado:** `IMPLEMENTED`. **Testes:** `test_tool_gateway.py`, `test_faults.py`,
  `test_authorization.py`.

### `tool_loop.py`
- **Responsabilidade:** `ToolCallingProvider` — injeta declarações no system
  prompt, interpreta JSON `{"tool","args"}`, executa via gateway, devolve
  `[TOOL_RESULT…]` como dado e repete até 4 rodadas.
- **Estado:** `IMPLEMENTED`. **Testes:** `test_tool_loop.py`.

## 6. Roteamento de modelos — Fase 3 (`ultron-2.0/ultron_2_0/routing/`)

### `__init__.py`
- **Responsabilidade:** exporta a API pública do pacote de roteamento
  (`ModelRouter`, `RouterConfig`, `RoutingProvider`, `ModelCatalog`,
  `ModelCapabilities`, `TaskType`, `infer_task_type`, `ModelSelectionPolicy`,
  `Candidate`, `FallbackManager`, `RetryManager`, `RetryPolicy`,
  `MetricsRegistry`, `ProviderAdapter`, `sanitize_error`, `AUTO_MODEL`).
- **Estado:** `IMPLEMENTED`.

### `router.py`
- **Responsabilidade:** `ModelRouter` envolve o `ProviderRegistry` do lain
  (autoridade de registro preservada) e é passado ao `Orchestrator` como
  `provider_registry` (duck typing). `RoutingProvider` é a fachada observável
  pelo orquestrador. `dispatch`/`iter_stream` executam inferência de tarefa,
  ranking da política, adaptador com timeout, fallback com retry/backoff e
  cooldown; métricas sanitizadas; `default_model` retorna `"auto"` no modo
  `auto`.
- **Entrada:** `RouterConfig` por env (`ULTRON_ROUTER_*`), sem credenciais.
- **Estado:** `IMPLEMENTED`. **Testes:** `tests/test_routing.py`.

### `capabilities.py`
- **Responsabilidade:** `TaskType` (chat/code/reasoning/long_context/cheap),
  `ModelCapabilities` (qualidade, janela, ferramentas, streaming, custo, tags),
  `infer_task_type` heurística determinística sem chamada de modelo, perfis
  conhecidos (`mock`, `gemini`).
- **Estado:** `IMPLEMENTED`.

### `catalog.py`
- **Responsabilidade:** `ModelCatalog` derivado dos provedores registrados;
  `build_catalog` a partir de `(provider_id, default_model)`; overrides de
  modelo por tarefa são decisões explícitas (`task_models`), não empate de
  score; `best_model` respeita override antes do ranking.
- **Estado:** `IMPLEMENTED`.

### `policy.py`
- **Responsabilidade:** `ModelSelectionPolicy` ranking determinístico de
  provedores por aderência à tarefa; `default_bonus` para o provedor padrão;
  `exclude` e `preferred` para controle do roteador.
- **Estado:** `IMPLEMENTED`.

### `retry.py`
- **Responsabilidade:** `RetryPolicy` (max_attempts, backoff exponencial
  limitado) e `RetryManager` — executa com retry, classifica transitórios como
  repetíveis e definitivos como não repetíveis, propaga a última exceção sem
  embrulho.
- **Estado:** `IMPLEMENTED`.

### `fallback.py`
- **Responsabilidade:** `FallbackManager` tenta candidatos em ordem com retry
  por provedor; falha de um não impede o próximo; métricas por provedor; última
  exceção propagada sem embrulho.
- **Estado:** `IMPLEMENTED`.

### `metrics.py`
- **Responsabilidade:** `MetricsRegistry` com contadores de chamadas/sucessos/
  falhas/retries, latência, cooldown; `sanitize_error` remove padrões de
  segredo (chave/token) e limita tamanho; snapshot público sem credenciais.
- **Estado:** `IMPLEMENTED`.

### `adapters.py`
- **Responsabilidade:** `ProviderAdapter` fixa o modelo do candidato na
  requisição (cópia, não muta o original), aplica `asyncio.wait_for` e converte
  estouro para `ProviderTimeoutError`, abre streams com timeout até o primeiro
  chunk (failover só antes de saída parcial).
- **Estado:** `IMPLEMENTED`.

### `marklvi_actions.py`
- **Responsabilidade:** adaptar 4 actions reais do Mark-LVI:
  `system_status`, `open_app`, `web_search`, `reminder`; `build_gateway()`.
- **Estado:** `IMPLEMENTED`. **Testes:** `test_integration_tools.py`.

### `memory_tools.py`
- **Responsabilidade:** `FactMemory` (fachada sobre
  `Mark-LVI-main/memory/memory_manager.py`) com `MEMORY_PATH` em
  `data/memory.json`, `_path_lock` e reafirmação de caminho; contratos
  `remember`/`recall`/`forget`; `register_memory_tools()` aceita `FactMemory` ou
  `MemoryEngine`.
- **Estado:** `IMPLEMENTED`.
- **Testes:** `test_memory_tools.py`, `test_memory_engine.py`.

### `memory_engine.py`
- **Responsabilidade:** memória tipada (`working/episodic/semantic/procedural/
  user`), escopos, trust, tags, retenção, TTL, deduplicação, atualização
  versionada, histórico, exclusão autorizada, consolidação somente leitura,
  orçamento de contexto e métricas. Persiste em `memory.json` (canônico) +
  `memory_records.json` + `memory_history.json`.
- **Interface:** `store`, `update`, `delete`, `search`, `retrieve`, `get_context`,
  `remember`, `recall`, `forget`, `consolidate`, `expire`, `entries`, `history`,
  `stats` (ver `docs/memory/MEMORY_API.md`).
- **Estado:** `IMPLEMENTED`.
- **Testes:** `test_memory_engine.py` (17).

### `memory_injection.py`
- **Responsabilidade:** `MemoryInjectionProvider` — recupera memória da última
  mensagem do usuário e anexa o bloco ao `system_instruction` (marcado como
  DADO), delegando identidade/streaming ao provedor interno. Uma recuperação por
  turno; falha de memória não derruba a conversa.
- **Estado:** `IMPLEMENTED`.
- **Testes:** `test_memory_engine.py`.

## 2. Voz (`ultron-2.0/ultron_2_0/voice/`)

| Módulo | Responsabilidade | Estado | Testes |
|---|---|---|---|
| `contracts.py` | taxas 16 kHz/24 kHz e helpers | `IMPLEMENTED` | `test_voice_pipeline.py` |
| `audio_io.py` | detecta `parec`/`arecord`/`aplay`/`paplay`; microfone e player por subprocesso | `IMPLEMENTED` | `test_voice_units.py`, `test_faults.py` |
| `stt_gemini.py` | `GeminiLiveSTT` (só transcrição) e `GeminiBatchTranscriber` | `IMPLEMENTED` | `test_voice_units.py` |
| `tts.py` | `GeminiTTS` (v1beta), `SystemSpeaker`, `NullSpeaker` | `IMPLEMENTED` | `test_voice_units.py`, validação ao vivo |
| `pipeline.py` | `VoicePipeline.handle_transcript`: bridge → texto → TTS opcional | `IMPLEMENTED` | `test_voice_pipeline.py`, `test_faults.py` |
| `runner.py` | CLI de voz (`--audio`, `--live`, `--list-devices`, `--no-tts`) | `IMPLEMENTED` | uso manual |
| `__main__.py` | `python -m ultron_2_0.voice` | `IMPLEMENTED` | — |

## 3. HUD (`ultron-2.0/ultron_2_0/web/`)

| Módulo | Responsabilidade | Estado | Testes |
|---|---|---|---|
| `app.py` | FastAPI: `/`, `/api/status`, `/api/system`, `/api/activity`, `/api/tools`, `/api/history`, `/api/chat`, `/api/new`, `/api/approvals` (+ approve/reject) | `IMPLEMENTED` | `test_web.py` (21) |
| `activity.py` | `ActivityLog`: ring buffer da sessão (turno/resposta/tool/erro/aprovação) | `IMPLEMENTED` | `test_web.py` |
| `server.py` | uvicorn, bind `127.0.0.1:8765`, ciclo de vida do bridge | `IMPLEMENTED` | `test_web.py` |
| `static/index.html` | UI local (tema ULTRON, canvas por estado real), sem CDN | `IMPLEMENTED` | `test_web.py` + smoke HTTP |

## 4. Testes (`ultron-2.0/tests/`)

`conftest.py`, `fakes.py` (`ScriptedProvider` implementa `LLMProvider`) e os 12
arquivos listados em `docs/TESTING.md`.

## 5. Originais reaproveitados

| Módulo original | Uso |
|---|---|
| `lain/app/core/orchestrator.py` | instanciado, não alterado |
| `lain/app/core/chat_service.py` | persistência |
| `lain/app/core/context_manager.py` | janela de contexto |
| `lain/app/intelligence/prompt_engine.py` | prompt/personalidade |
| `lain/app/intelligence/providers/*` | contrato e registry |
| `lain/app/database/*` | modelos/repositórios |
| `lain/app/config.py` | `Settings` |
| `Mark-LVI-main/memory/memory_manager.py` | armazenamento de fatos |
| `Mark-LVI-main/actions/system_monitor.py` | helper `get_system_status` |
| `Mark-LVI-main/actions/open_app.py` | ação |
| `Mark-LVI-main/actions/web_search.py` | ação |
| `Mark-LVI-main/actions/reminder.py` | ação |

## 7. Fora de escopo / não usados

- `Mark-LVI-main/main.py`, `ui.py`, `dashboard/`: runtime/HUD originais.
- `Mark-LVI-main/core/stt.py`, `core/tts.py`: código morto.
- `Mark-LVI-main/providers/`: stack opcional não instalada.
- `lain/app/api/*`, `lain/app/main.py`: API do lain não executada no 2.0.
- Actions de escrita/execução: bloqueadas por segurança.
