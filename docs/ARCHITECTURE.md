# ARCHITECTURE — ULTRON 2.0

Este documento descreve a arquitetura **realmente implementada** em `ultron-2.0/`.
Onde algo ainda não existe, está marcado como pendente — nada aqui é aspiracional
sem essa marcação. A auditoria que originou as decisões está em
`docs/INTEGRATION_AUDIT.md`.

## 1. Princípio de autoridade

```text
Usuário
  │
  ▼
Interface (CLI de texto · voz · HUD web)
  │
  ▼
OrchestratorBridge            ← estado de interface (conversation_id da sessão)
  │
  ▼
Orchestrator do lain          ← ÚNICO ciclo de conversa, contexto e persistência
  │  ├── ChatService (SQLite do 2.0)
  │  ├── ContextManager + PromptEngine
  │  └── ProviderRegistry
  │        └── ModelRouter  (Fase 3: seleção/fallback; não é orquestrador)
              └── MemoryInjectionProvider  ← extensão 2.0 (memória por turno)
  │              └── ToolCallingProvider ← extensão 2.0, mesmo provider_id
  │                    └── ToolGateway   ← allowlist, validação, timeout, auditoria
  M-bM-^TM-^B                    M-bM-^TM-^TM-bM-^TM-^@M-bM-^TM-^@ AgentOrchestrator  (Fase 4: coordenação de agentes especializados; não é orquestrador conversacional)
  M-bM-^TM-^B                    M-bM-^TM-^TM-bM-^TM-^@M-bM-^TM-^@ IntegrationOrchestrator  (Fase 5: integracao CLI/MCP; nao e orquestrador conversacional)
  │                          └── actions do Mark-LVI (worker threads)
  ▼
Sistema operacional
```

Regras efetivas:

- **ULTRON é o único núcleo de decisão.** Não existe segundo orquestrador, eco
  por regex, nem fallback de comando.
- **Mark-LVI é fonte de componentes operacionais** (actions e infraestrutura),
  não autoridade de conversa. Seu `main.py`, histórico, sessão viva e provider
  registry **não** são executados pelo ULTRON 2.0.
- **Uma conversa, um histórico.** Todo turno — texto, voz ou HUD — passa por
  `OrchestratorBridge.process_text`, que reusa o `conversation_id` da sessão.
- **A voz é interface.** O Gemini Live entra apenas como STT; o texto segue o
  caminho do núcleo (ver `docs/VOICE_PIPELINE.md`).

## 2. Estrutura implementada

```text
ultron-2.0/
├── README.md
├── pyproject.toml / requirements.txt
├── __main__.py                     # python -m ultron_2_0 (re-export)
├── data/                           # banco e memória do 2.0 (nunca os originais)
├── scripts/run_demo.py
├── ultron_2_0/
│   ├── bootstrap.py                # caminhos absolutos, Settings, banco isolado
│   ├── core_runtime.py             # wiring do núcleo lain + loop dedicado
│   ├── orchestrator_bridge.py      # ponta de entrada única (texto/voz/web)
│   ├── tool_contracts.py           # ToolContract / ToolResult / ToolExecutor
│   ├── tool_gateway.py             # allowlist, validação, timeout, autorização, auditoria
│   ├── authorization.py            # PendingAction/token de uso único/expiração
│   ├── tool_loop.py                # ToolCallingProvider (protocolo JSON)
│   ├── marklvi_actions.py          # subset curado das actions
│   ├── memory_tools.py             # FactMemory + remember/recall/forget
│   ├── memory_engine.py            # tipos/escopo/versão/retenção/consolidação
│   ├── memory_injection.py         # memória no prompt (1×/turno)
│   ├── cli.py                      # interface de texto
│   ├── voice/                      # STT, TTS, áudio, pipeline (interface)
│   └── web/                        # HUD FastAPI/uvicorn (interface)
└── tests/                          # 136 testes (ver docs/TESTING.md)
```

`lain/` e `Mark-LVI-main/` são **importados via `sys.path`**, nunca copiados nem
modificados. O `bootstrap.ensure_sys_paths()` resolve as duas raízes por caminho
absoluto, de modo que a execução é independente do CWD.

## 3. Camadas e responsabilidades

### 3.1 Interface

| Interface | Arquivo | Responsabilidade |
|---|---|---|
| CLI de texto | `ultron_2_0/cli.py`, `python -m ultron_2_0` | REPL, `/status`, `/tools`, `/new`, modo `--demo` e one-shot |
| Voz | `ultron_2_0/voice/` | microfone → STT → núcleo → TTS (ou texto) |
| HUD web | `ultron_2_0/web/` | estado real + chat local em `127.0.0.1` |

Nenhuma interface guarda histórico próprio. O `conversation_id` pertence ao
`OrchestratorBridge` (estado da sessão de interface), e as mensagens são
persistidas pelo `ChatService` do lain.

### 3.2 Núcleo

`UltronCoreRuntime` (`core_runtime.py`) monta, por composição, os módulos
originais do lain:

```text
Settings → engine + session_factory (banco do 2.0)
ConversationRepository / MessageRepository
ChatService → ContextManager → PromptEngine
ProviderRegistry (mock + gemini quando há chave)
ModelRouter (Fase 3: seleção/fallback sobre o registry)
Orchestrator
```

Dois modos de ciclo de vida:

- `start_background()` + `chat_sync()` / `run_coro()`: loop dedicado em thread
  (usado pela CLI, voz e HUD). Necessário porque a sessão SQLAlchemy pertence a
  um único event loop; leituras de outro loop passam por `run_coro`.
- `start_async()` + `await chat()` / `await shutdown()`: para contextos já
  assíncronos (testes).

### 3.3 Provedores

O `ProviderRegistry` do lain continua sendo a autoridade. Cada provedor é
envolvido por `ToolCallingProvider` **sob o mesmo `provider_id`**, então o
orquestrador não percebe a extensão. O proxy:

1. injeta as declarações das ferramentas no system prompt (formato do próprio
   Mark-LVI, `providers/schema.py::to_prompt`);
2. aceita a resposta final em texto **ou** um único objeto
   `{"tool": "<nome>", "args": {...}}`;
3. valida e executa pelo gateway, devolve o resultado como dado marcado
   `[TOOL_RESULT …]` e chama o modelo de novo, até um teto de rodadas (4).

Consequência documentada: neste modo o streaming incremental não é usado — a
resposta final chega como um único chunk.

Por fora do `ToolCallingProvider` (quando a memória está ativa) fica o
`MemoryInjectionProvider`: ele recupera o bloco de memória **uma vez por turno**
e o anexa ao `system_instruction`; a identidade do provider é preservada. A
ordem importa — ferramentas por dentro, memória por fora — para que as rodadas
internas de ferramenta não disparem nova recuperação.

### 3.3a Model Router (Fase 3)

O `ModelRouter` (`ultron_2_0/routing/router.py`) é uma camada de seleção e
encaminhamento, **não um segundo orquestrador**. Ele envolve o
`ProviderRegistry` do lain — que continua sendo a autoridade de registro — e
é passado ao `Orchestrator` no lugar do registry (duck typing). O contrato do
lain (`default_provider_id`, `get_provider`, `list_providers`,
`register_provider`) é preservado.

Componentes do pacote `routing/`:

| Módulo | Responsabilidade |
|---|---|
| `router.py` | `ModelRouter`, `RouterConfig`, `RoutingProvider`; `dispatch`/`iter_stream` executam inferência de tarefa → ranking da política → adaptador com timeout → fallback com retry/backoff/cooldown |
| `capabilities.py` | `TaskType`, `ModelCapabilities`, `infer_task_type` (heurística sem chamada de modelo) |
| `catalog.py` | `ModelCatalog`, `build_catalog`; overrides de modelo por tarefa são decisões explícitas |
| `policy.py` | `ModelSelectionPolicy` — ranking determinístico com bônus ao provedor padrão |
| `retry.py` | `RetryPolicy`/`RetryManager` — backoff exponencial, classificação de erros, última exceção sem embrulho |
| `fallback.py` | `FallbackManager` — tenta candidatos em ordem; falha de um não impede o próximo |
| `metrics.py` | `MetricsRegistry` — contadores, cooldown, `sanitize_error` sem credenciais |
| `adapters.py` | `ProviderAdapter` — fixa modelo na requisição, `asyncio.wait_for`, stream com timeout até o 1º chunk |

Regras de projeto (ADR-014):

- o provedor padrão continua sendo o primário; a política ordena os demais
  apenas como fallback;
- fallback entre provedores é **opt-in** (`ULTRON_ROUTER_FALLBACK`, default 0);
- `mock` nunca é fallback automático (`allow_mock_fallback`);
- provedor/modelo escolhidos explicitamente são respeitados e desligam o
  fallback daquele turno;
- em `mode="auto"` (opt-in via `ULTRON_ROUTER_MODE`), a política escolhe o
  provedor por tipo de tarefa e `RoutingProvider.default_model` retorna o
  sentinela `"auto"`; o modelo real é escolhido por tarefa e gravado na
  mensagem do assistente;
- retry classifica transitórios como repetíveis e definitivos como não
  repetíveis; a última exceção é propagada sem embrulho;
- métricas e snapshots nunca expõem credenciais (`sanitize_error`).

### 3.3b Sistema Multiagente (Fase 4)

O `AgentOrchestrator` (`ultron_2_0/agents/agent_orchestrator.py`) é a
autoridade central de coordenação de agentes especializados. Não é um
segundo orquestrador conversacional: não toca no histórico, na memória
canônica nem no `process_text`. Ele coordena agentes sob solicitação do
ULTRON, com isolamento de contexto e rastreabilidade.

Componentes do pacote `agents/`:

| Módulo | Responsabilidade |
|---|---|
| `agent_orchestrator.py` | `AgentOrchestrator` — ciclo de vida das tarefas, delegação, validação, monitoramento |
| `agent_registry.py` | `AgentRegistry` — registro e descoberta de agentes por tipo/capacidade |
| `agent_task.py` | `AgentTask`, `AgentResult`, `AgentCapability`, `TaskState` — contratos de dados |
| `task_queue.py` | `TaskQueue` — fila com isolamento de arquivos para tarefas concorrentes |
| `agent_validator.py` | `AgentValidator` — validação determinística de resultados (não confiáveis até validar) |
| `result_manager.py` | `ResultManager` — recebe, valida e armazena resultados para avaliação do ULTRON |
| `execution_monitor.py` | `ExecutionMonitor` — observabilidade de execução (sem credenciais) |
| `implementations.py` | 6 agentes iniciais como adaptadores sobre ferramentas existentes |

Regras de projeto (AGENTS.md §4, §5):

- Agentes possuem responsabilidades delimitadas; cada um recebe apenas o
  contexto necessário (isolamento).
- A comunicação utiliza contratos estruturados (`AgentTask`/`AgentResult`).
- Resultados são enviados ao ULTRON para avaliação centralizada.
- Agentes não modificam diretamente a memória canônica sem autorização.
- Alterações de código possuem isolamento e rastreabilidade.
- Tarefas concorrentes evitam conflitos de arquivos (`TaskQueue`).
- Resultados possuem identificação de origem.
- Falhas de agentes são detectadas e registradas (replanejamento com tentativas).
- A primeira implementação utiliza agentes externos existentes quando viável
  (Fase 5: OpenCode, Claude Code, MCP); não cria modelos próprios para o que
  já existe.

Integrado a `core_runtime.py` (6 agentes iniciais registrados) e exposto via
`orchestrator_bridge.status()["agents"]`.

### 3.3c Integrações externas — Agentes CLI e MCP (Fase 5)

O `IntegrationOrchestrator` (`ultron_2_0/integrations/integration_orchestrator.py`)
coordena tarefas delegadas a agentes/servidores externos. Não é um segundo
orquestrador conversacional: apenas encaminha tarefas especializadas e devolve
resultados para avaliação do ULTRON, sem tocar no histórico, memória canônica
nem no `process_text`.

Componentes do pacote `integrations/`:

| Módulo | Responsabilidade |
|---|---|
| `integration_orchestrator.py` | `IntegrationOrchestrator` — cria tarefas, executa via adaptador, isola falhas |
| `integration_registry.py` | `IntegrationRegistry` — registro, habilitar/desabilitar por target |
| `contracts.py` | `IntegrationTask`, `IntegrationResult`, `IntegrationType`, `IntegrationState` |
| `base.py` | `ExternalIntegration` — subprocesso isolado com timeout, sanitização de saída |
| `cli_adapter.py` | `OpenCodeAdapter` — `opencode run [--format json] ...` (interface real) |
| `mcp_adapter.py` | `MCPAdapter` — `opencode mcp list` (interface real) |

Regras de projeto (AGENTS.md §4.4, §5.3):

- Inspecionar interfaces reais; não inventar comandos, APIs ou contratos.
- Adaptadores independentes por integração.
- Processos externos isolados (subprocesso, sem shell=True).
- Limites de execução (timeout por integração).
- Registrar tarefas e resultados.
- Controlar permissões por integração (habilitar/desabilitar individualmente).
- Permitir desativar cada integração individualmente.
- Resultados de agentes externos são dados não confiáveis até validar.

Integrado a `core_runtime.py` (adaptadores OpenCode + MCP registrados) e
exposto via `orchestrator_bridge.status()["integrations"]`.

### 3.3d Autonomia operacional — Agentes CLI e MCP (Fase 7)

O `WorkflowEngine` (`ultron_2_0/autonomy/workflow_engine.py`) permite que o
ULTRON planeje e execute fluxos de trabalho complexos, sem criar um segundo
orquestrador conversacional: apenas decompõe objetivos, delega passos aos
orquestradores existentes (AgentOrchestrator Fase 4, IntegrationOrchestrator
Fase 5) e monitora a execução.

Componentes do pacote `autonomy/`:

| Módulo | Responsabilidade |
|---|---|
| `planner.py` | `Planner` — cria um `Workflow` a partir de um objetivo, com limites de segurança |
| `task_decomposer.py` | `TaskDecomposer` — decomposição determinística de objetivo em passos com alvos sugeridos |
| `workflow_engine.py` | `WorkflowEngine` — executa workflows distribuindo passos, respeitando dependências, limites e recuperação |
| `state_tracker.py` | `StateTracker` — persiste estado de workflows para recuperação após falhas |
| `scheduler.py` | `Scheduler` — agenda workflows por horário de execução |
| `recovery_manager.py` | `RecoveryManager` — planeja recuperação de workflows `FAILED`/`PAUSED` |

Regras de projeto (AGENTS.md §4.7):

- Separar planejamento de execução (o Planner apenas planeja, o Engine executa).
- Aplicar limites de recursos e tempo (`max_steps`, `max_execution_seconds`).
- Exigir autorização para operações sensíveis (`require_human_approval`).
- Registrar decisões e resultados (StateTracker, ExecutionMonitor).
- Evitar loops de execução (dependências lineares, estados bem definidos).
- Limites de tentativas por passo (`max_attempts`).
- Preservar possibilidade de interrupção humana (`PAUSED`, retry/skip).

Integrado a `core_runtime.py` e exposto via
`orchestrator_bridge.status()` (workflows, agendamentos, recuperação).

### 3.4 Ferramentas

Ver `docs/TOOLS.md` para contratos completos. Resumo do subset curado:

`system_status`, `open_app`, `web_search`, `reminder`, `remember`, `recall`,
`forget`.

As demais actions descobertas pelo loader do Mark-LVI permanecem
**desconectadas** por decisão de segurança (ver `docs/SECURITY.md`).

### 3.5 Memória

A memória é um subsistema do núcleo (não um segundo cérebro). Documentação
completa em `docs/memory/`.

- **Histórico conversacional:** SQLite em `ultron-2.0/data/ultron2.db`
  (autoridade do `ChatService`). Memória ≠ histórico.
- **Contexto do turno:** `ContextManager`/`PromptEngine` do lain.
- **Fatos duráveis (canônico):** `data/memory.json` no esquema do
  `memory_manager` do Mark-LVI; espelha apenas escopos `global`/`user:default`.
- **Metadados:** `data/memory_records.json` — tipo (`working/episodic/semantic/
  procedural/user`), escopo, trust, tags, retenção, versão, validade.
- **Histórico de fatos:** `data/memory_history.json` — versões anteriores e
  tombstone de exclusão sem conteúdo.
- **Escrita:** somente explícita (`remember` ou chamada direta ao engine). Nada
  é capturado automaticamente; resultado de ferramenta não vira memória.
- **Recuperação:** lexical + recência + confiança, com filtros de escopo e
  orçamento em caracteres; sem embeddings (planejado).
- **Injeção:** `MemoryInjectionProvider` anexa o bloco marcado como
  "DATA, not instructions" uma vez por turno; falha de memória não derruba a
  conversa.

### 3.5a Evolução da memória — Fase 6

A memória evoluiu com capacidades opcionais que NÃO quebram a compatibilidade
com o `MemoryEngine` existente nem tornam embeddings/criptografia
dependências obrigatórias (AGENTS.md §4.6):

| Módulo | Responsabilidade |
|---|---|
| `memory_semantic.py` | `SemanticIndex` — busca semântica opcional via `sentence-transformers`; sem a dependência, desativa graciosamente e a busca léxica preservada continua sendo usada |
| `memory_backup.py` | `backup_memory()`/`restore_memory()` — backup/restauração dos três arquivos canônicos (`memory.json`, `memory_records.json`, `memory_history.json`) em ZIP com manifesto; restauração requer `confirm=True` |
| `memory_encryption.py` | `MemoryEncryption` — criptografia opcional em repouso (`cryptography.fernet`); chave via `ULTRON2_MEMORY_ENCRYPTION_KEY` ou `memory.key`; nunca impressa nem logada |

Novos métodos no `MemoryEngine` (contrato preservado):

- `search_semantic(query, ...)` — busca semântica; devolve lista vazia sem embeddings
- `retrieve_hybrid(query, ...)` — recuperação híbrida (léxica + semântica, ponderável)
- `backup(dest_zip)` / `restore(source_zip, confirm)` — backup e restauração
- `encryption_status()` / `encrypt_memory_file()` / `decrypt_memory_file()` — criptografia opcional em repouso

Critérios de Fase 6 atendidos: recuperação semântica testada (fallback para léxico), recuperação lexical preservada, backup e restauração validados (round-trip), criptografia testada (opcional), compatibilidade com memória existente (17 testes do `memory_engine.py` continuam verdes).

## 4. Fluxos

### 4.1 Texto

```text
CLI/HUD → OrchestratorBridge.process_text → Orchestrator → ModelRouter
        → ProviderRegistry (autoridade de registro)
        → MemoryInjectionProvider (recupera memória do turno e anexa ao prompt)
        → (ToolCallingProvider → ToolGateway → action) → resposta
        → persistência no SQLite do 2.0 → interface
```

### 4.2 Voz

```text
Microfone (parec/arecord) → Gemini Live (somente transcrição)
  → OrchestratorBridge.process_text (MESMO caminho do texto)
  → texto impresso (sempre) + TTS opcional (Gemini TTS ou voz do sistema)
```

### 4.3 Ferramenta

```text
mensagem → orquestrador → modelo decide {"tool": …}
  → gateway valida contrato/permissões
  → [se requires_confirmation] AuthorizationManager: pedido → interface
    (CLI/HUD) decide → token de uso único → consume
  → executa em worker thread com timeout
  → ToolResult (status=done/unverified/failed)
  → volta ao modelo como DADO não confiável → resposta final
```

## 5. Segurança e limites

Detalhes em `docs/SECURITY.md`. Resumo:

- allowlist por contrato: ferramenta sem contrato não executa;
- validação de campos obrigatórios, tipos e parâmetros desconhecidos;
- timeout por ferramenta e execução fora do event loop;
- auditoria em logger dedicado (`ultron2.tools.audit`);
- ações sensíveis passam pelo `AuthorizationManager` (`ultron_2_0/authorization.py`):
  pedido → decisão da interface (CLI `[s/N]` ou HUD) → token de uso único
  vinculado a ferramenta + argumentos, com expiração e proteção contra replay;
  sem manager o gateway recusa e **a voz sempre recusa**;
- nenhuma execução de shell irrestrita é exposta;
- segredos nunca são logados nem duplicados; `config/api_keys.json` do Mark-LVI
  não é criado nem editado;
- memória: escopo validado, leitura filtrada, recusa de credenciais, exclusão
  com autorização explícita, tombstone sem conteúdo, consolidação somente
  leitura e bloco recuperado marcado como DADO (não instrução).

## 6. O que não está integrado (pendências explícitas)

| Item | Situação | Motivo |
|---|---|---|
| Wake word / VAD | **não integrados** | dependência `openwakeword` ausente; não há VAD validado no ambiente |
| Confirmação interativa de ações destrutivas | **implementada (Fase 2)** | `AuthorizationManager` + CLI + HUD; voz sempre recusa |
| `browser_control`, `file_controller`, `computer_settings`, `dev_agent`, `code_helper`, `file_processor`, `game_updater` | **desconectadas** | riscos S1–S4 da auditoria (shell=True, execução de código, FAILSAFE desativado) |
| Streaming incremental de resposta | **não usado** | o protocolo de ferramentas exige a resposta completa |
| Busca semântica (embeddings) | **não implementada** | nenhum provedor/configuração; lexical + recência cobre o uso atual |
| Captura automática de memória | **não desejada** | política explícita: só `remember`/engine grava |
| Relações entre entidades (grafo) | **não implementado** | sem necessidade demonstrada |
| Tool calling nativo do provedor | **não usado** | o `LLMRequest` do lain não carrega tools; extensão via proxy de prompt |
| Interface Qt | **descartada** | decisão nº 6: HUD web usa FastAPI/uvicorn já presentes, adequado a ~4 GB de RAM |

## 7. Decisões arquiteturais aplicadas

1. `google-genai` 3.0.0 (`>=3.0.0,<4`) no venv dedicado do 2.0.
2. Venv próprio em `ultron-2.0/.venv` (Python 3.12, criado com `uv`).
3. Subset curado de actions: `system_status`, `open_app`, `web_search`,
   `reminder` (+ tools de memória).
4. Memória reutiliza `memory_manager` do Mark-LVI gravando em arquivo do 2.0.
5. Banco isolado `data/ultron2.db`; `.env` do lain por caminho absoluto.
6. HUD web em vez de Qt.
7. Memória tipada evolui o armazenamento real (`memory.json` + sidecars), sem
   segundo banco e sem embeddings obrigatórios.
8. Injeção de memória fica fora do `ToolCallingProvider` (1×/turno), preservando
   um único orquestrador e sem histórico paralelo.

A justificativa de cada decisão e os riscos associados estão em
`docs/INTEGRATION_AUDIT.md`.
