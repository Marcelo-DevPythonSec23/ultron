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

## 7. Sistema Multiagente — Fase 4 (`ultron-2.0/ultron_2_0/agents/`)

### `__init__.py`
- **Responsabilidade:** exporta a API pública do sistema multiagente
  (`AgentOrchestrator`, `AgentRegistry`, `AgentTask`, `AgentResult`,
  `AgentCapability`, `TaskState`, `BaseAgent`, `TaskQueue`, `ResultManager`,
  `AgentValidator`, `ExecutionMonitor`, e os agentes iniciais).
- **Estado:** `IMPLEMENTED`. **Testes:** `tests/test_agents.py`.

### `agent_task.py`
- **Responsabilidade:** contratos de dados `AgentTask` (tarefa com ciclo de
  vida `pending→assigned→running→review→completed/failed/cancelled`),
  `AgentResult` (resultado com identificação de origem), `AgentCapability`
  e `TaskState` (estados permitidos e transições válidas).
- **Estado:** `IMPLEMENTED`.

### `agent_registry.py`
- **Responsabilidade:** `AgentRegistry` — catálogo central de agentes
  especializados, registro, descoberta por tipo/capacidade e seleção para
  tarefas. Preserva a autoridade central do ULTRON (nenhum histórico
  paralelo nem memória independente).
- **Estado:** `IMPLEMENTED`.

### `agent_orchestrator.py`
- **Responsabilidade:** `AgentOrchestrator` — autoridade central de
  coordenação de agentes. Controla o ciclo de vida das tarefas, delega
  execução a agentes via registry, coordena fila com isolamento de arquivos
  (`TaskQueue`), valida resultados (`AgentValidator`/`ResultManager`) e
  monitora (`ExecutionMonitor`). Não é um segundo orquestrador conversacional.
- **Estado:** `IMPLEMENTED`. Integrado a `core_runtime.py` e exposto via
  `orchestrator_bridge.status()["agents"]`.

### `task_queue.py`
- **Responsabilidade:** `TaskQueue` — fila ordenada com controle de
  concorrência; evita que duas tarefas concorrentes modifiquem os mesmos
  arquivos simultaneamente (AGENTS.md §5.4); respeita dependências entre
  tarefas.
- **Estado:** `IMPLEMENTED`.

### `agent_validator.py`
- **Responsabilidade:** `AgentValidator` — validação determinística de
  resultados de agentes (dados não confiáveis até validar): identificação
  de origem, consistência de task_id, conteúdo não vazio, arquivos dentro do
  escopo, erro registrado em falhas.
- **Estado:** `IMPLEMENTED`.

### `result_manager.py`
- **Responsabilidade:** `ResultManager` — recebe, valida e armazena
  resultados de agentes; expõe ao `AgentOrchestrator` para avaliação
  centralizada pelo ULTRON. Nunca aplica resultados automaticamente à
  memória canônica.
- **Estado:** `IMPLEMENTED`.

### `execution_monitor.py`
- **Responsabilidade:** `ExecutionMonitor` — observabilidade de execução:
  tarefa, agente, tempo, estado, falhas, tentativas, validação. Sem
  credenciais nem dados sensíveis nos logs.
- **Estado:** `IMPLEMENTED`.

### `implementations.py`
- **Responsabilidade:** agentes iniciais especializados como adaptadores
  sobre ferramentas existentes do ULTRON (não modelos próprios para o que
  já existe): `DeveloperAgent` (inspeção/proposta de código), `ResearchAgent`
  (pesquisa via web_search + memória), `SecurityAgent` (auditoria de
  contratos e permissões), `QAAgent` (execução de testes),
  `DatabaseAgent` (inspeção somente leitura de banco), `ArchitectureAgent`
  (revisão de ADRs e decisões técnicas).
- **Estado:** `IMPLEMENTED`. 6 agentes iniciais registrados no runtime.

## 9. Evolução da memória — Fase 6 (`ultron-2.0/ultron_2_0/`)

### `memory_semantic.py`
- **Responsabilidade:** `SemanticIndex` — busca semântica OPCIONAL sobre
  registros de memória. Tenta usar `sentence-transformers` se instalado; se
  não estiver, desativa graciosamente (`available=False`) e a memória cai de
  volta para a busca léxica do `MemoryEngine` (recuperação lexical
  preservada). Não é dependência obrigatória (AGENTS.md §4.6).
- **Estado:** `IMPLEMENTED`.

### `memory_backup.py`
- **Responsabilidade:** `backup_memory()` / `restore_memory()` — backup e
  restauração dos três arquivos canônicos da memória do 2.0
  (`memory.json`, `memory_records.json`, `memory_history.json`) em ZIP com
  manifesto de metadados (sem expor conteúdo dos fatos). Não destrutivo:
  backup só lê; restauração requer `confirm=True`.
- **Estado:** `IMPLEMENTED`.

### `memory_encryption.py`
- **Responsabilidade:** `MemoryEncryption` / `generate_key_file()` —
  criptografia OPCIONAL em repouso (`cryptography.fernet`). Chave via
  `ULTRON2_MEMORY_ENCRYPTION_KEY` ou arquivo `memory.key`. Nunca imprime,
  loga ou duplica a chave. Se indisponível, desativa graciosamente.
- **Estado:** `IMPLEMENTED`.

### `memory_engine.py` (métodos Fase 6)
- `search_semantic()` — busca semântica (fallback para léxico sem embeddings).
- `retrieve_hybrid()` — recuperação híbrida (léxica + semântica, ponderável).
- `backup()` / `restore()` — backup e restauração da memória.
- `encryption` / `encryption_status()` / `encrypt_memory_file()` /
  `decrypt_memory_file()` — criptografia opcional em repouso.
- Todos os métodos existentes (store, search, retrieve, get_context,
  consolidate, expire, stats, etc.) preservados sem alteração de contrato.
- **Estado:** `IMPLEMENTED` (extensão compatível).

## 8. Integrações externas — Fase 5 (`ultron-2.0/ultron_2_0/integrations/`)

### `__init__.py`
- **Responsabilidade:** exporta a API pública de integrações externas
  (`IntegrationOrchestrator`, `IntegrationRegistry`, `ExternalIntegration`,
  `OpenCodeAdapter`, `MCPAdapter`, contratos de dados).
- **Estado:** `IMPLEMENTED`. **Testes:** `tests/test_integrations.py`.

### `contracts.py`
- **Responsabilidade:** contratos de dados `IntegrationTask`, `IntegrationResult`,
  `IntegrationType` (cli/mcp), `IntegrationState` e `IntegrationCapability`.
- **Estado:** `IMPLEMENTED`.

### `base.py`
- **Responsabilidade:** `ExternalIntegration` — executa processo externo como
  subprocesso isolado com `asyncio.create_subprocess_exec` (sem shell=True),
  timeout com `asyncio.wait_for`, parse de saída e sanitização de credenciais
  (`sanitize_output`).
- **Estado:** `IMPLEMENTED`.

### `cli_adapter.py`
- **Responsabilidade:** `OpenCodeAdapter` — adaptador para o agente CLI OpenCode
  sobre a interface real `opencode run [--format json] [--session] [--model]
  [--agent] [--auto] <mensagem>`. Parseia saída JSON ou texto bruto.
- **Estado:** `IMPLEMENTED`.

### `mcp_adapter.py`
- **Responsabilidade:** `MCPAdapter` — adaptador para servidores MCP sobre a
  interface real `opencode mcp list`. Lista servidores configurados; execução
  de tarefa MCP real requer servidor ativo (nao disponível neste ambiente),
  relatado de forma controlada.
- **Estado:** `IMPLEMENTED`.

### `integration_registry.py`
- **Responsabilidade:** `IntegrationRegistry` — catalogo de integracões
  registradas, habilitar/desabilitar individualmente por target, listar por tipo.
- **Estado:** `IMPLEMENTED`.

### `integration_orchestrator.py`
- **Responsabilidade:** `IntegrationOrchestrator` — cria tarefas de integracao,
  executa via adaptador registrado com timeout, isola falhas, nao e um segundo
  orquestrador conversacional (nao toca historico/memoria/process_text).
- **Estado:** `IMPLEMENTED`. Integrado a `core_runtime.py` (OpenCode + MCP
  registrados) e exposto via `orchestrator_bridge.status()["integrations"]`.

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
