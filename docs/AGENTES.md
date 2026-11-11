# AGENTES — Sistema Multiagente do ULTRON 2.1 (Fase 4)

> **Status:** IMPLEMENTADO (Fase 4 concluída). Ver `docs/context/TECHNICAL_DECISIONS.md`
> (ADR-015), `tests/test_agents.py` (19 testes) e
> `docs/roadmap/ULTRON_21_PHASE4_REPORT.md`.

## 1. Objetivo

Permitir que o ULTRON coordene agentes especializados e delegue tarefas,
preservando-se como a única autoridade de conversação, memória e orquestração
(AGENTS.md §3.2, §4, §5).

O `AgentOrchestrator` é a autoridade central de coordenação de agentes. Não é
um segundo orquestrador conversacional: não toca no histórico de conversa,
nem na memória canônica, nem no caminho único `process_text`.

## 2. Arquitetura do pacote `agents/`

```
ultron_2_0/agents/
├── __init__.py            # API pública (inclui agentes iniciais)
├── agent_task.py          # AgentTask, AgentResult, AgentCapability, TaskState, new_task_id
├── agent_registry.py      # AgentRegistry (registro e descoberta)
├── agent_orchestrator.py  # AgentOrchestrator (ciclo de vida das tarefas)
├── agent_validator.py     # AgentValidator (validação de resultados)
├── result_manager.py      # ResultManager (armazenamento e validação)
├── execution_monitor.py   # ExecutionMonitor (observabilidade)
├── task_queue.py          # TaskQueue (fila com isolamento de arquivos)
└── implementations.py     # 6 agentes iniciais (adaptadores, não modelos próprios)
```

## 3. Contratos de dados (`agent_task.py`)

### `TaskState` — estados permitidos (AGENTS.md §7)

```
pending → assigned → running → review → completed
                              ↘        ↘
                               failed ← (replanejamento: failed → pending)
                               cancelled
```

Transições válidas são aplicadas pelo `AgentTask.can_transition()`.

### `AgentTask`

Uma tarefa delegada a um agente especializado, com: identificador, objetivo,
descrição, tipo do agente, contexto, dependências, arquivos envolvidos,
permissões, estado, resultado, erro, tentativas e timestamps.

### `AgentResult`

Resultado estruturado com identificação de origem (`agent_id`, `agent_type`),
`task_id`, sucesso/falha, conteúdo, sumário, arquivos modificados, validação
e erro.

## 4. Componentes

| Módulo | Classe | Responsabilidade |
|---|---|---|
| `agent_orchestrator.py` | `AgentOrchestrator` | Ciclo de vida das tarefas, delegação a agentes, validação, monitoramento |
| `agent_registry.py` | `AgentRegistry` | Catálogo central: registro, descoberta por tipo/capacidade, seleção para tarefa |
| `agent_validator.py` | `AgentValidator` | Validação determinística (origem, task_id, conteúdo, escopo, erro) |
| `result_manager.py` | `ResultManager` | Recebe, valida e armazena resultados para avaliação do ULTRON |
| `execution_monitor.py` | `ExecutionMonitor` | Observabilidade: tarefa, agente, tempo, estado, falhas, tentativas |
| `task_queue.py` | `TaskQueue` | Fila ordenada com isolamento de arquivos (concorrência segura) |
| `implementations.py` | 6 agentes iniciais | Adaptadores sobre ferramentas existentes |

## 5. Agentes iniciais (6)

Todos são **adaptadores** sobre ferramentas existentes do ULTRON — não criam
modelos próprios para funcionalidades já oferecidas (AGENTS.md §4.3):

| Agente | Tipo | Capacidades |
|---|---|---|
| `DeveloperAgent` | `developer` | `inspect_code` (leitura), `propose_code_change` (requer autorização) |
| `ResearchAgent` | `research` | `research_topic` (web_search + memória) |
| `SecurityAgent` | `security` | `audit_tool_contract` (permissões, segredos, validação) |
| `QAAgent` | `qa` | `run_tests` (execução de suítes de teste) |
| `DatabaseAgent` | `database` | `inspect_schema` (banco, somente leitura) |
| `ArchitectureAgent` | `architecture` | `review_decision` (revisão de ADRs) |

Cada agente recebe apenas o contexto necessário para sua tarefa (isolamento)
e devolve um `AgentResult` para avaliação centralizada.

## 6. Regras de projeto (AGENTS.md §4, §5)

1. **Responsabilidades delimitadas:** cada agente tem um papel definido.
2. **Isolamento:** cada tarefa recebe apenas o contexto necessário.
3. **Contratos estruturados:** comunicação via `AgentTask`/`AgentResult`.
4. **Avaliação centralizada:** resultados vão ao ULTRON (`AgentOrchestrator`),
   nunca são aplicados automaticamente.
5. **Sem memória canônica direta:** agentes não modificam a memória canônica
   sem autorização (Fase 2).
6. **Isolamento de arquivos:** tarefas concorrentes não tocam os mesmos
   arquivos simultaneamente (`TaskQueue`).
7. **Identificação de origem:** todo resultado tem `agent_id`/`agent_type`.
8. **Falhas detectadas e registradas:** exceções de agente não derrubam o
   núcleo; replanejamento com tentativas (`max_attempts`).
9. **Agentes externos primeiro:** a primeira implementação utiliza agentes
   externos existentes quando viável (Fase 5: OpenCode, Claude Code, MCP).

## 7. Fluxo de execução de uma tarefa

```text
create_task()
  → TaskQueue.enqueue (estado: pending)
  → run_ready()
     → TaskQueue.next_ready()  (verifica dependências + isolamento de arquivos)
        → AgentRegistry.select_for_task()  (escolhe agente do tipo)
           → Agent.run()  (com timeout, exceções capturadas)
              → AgentValidator.validate()  (dados não confiáveis até validar)
                 → ResultManager.submit()  (armazena + valida)
                    → task estado: completed / failed
                       → se falhou e attempts < max_attempts: replaneja (pending)
```

## 8. Integração no núcleo

`ultron_2_0/core_runtime.py`:

- Cria `AgentOrchestrator(max_concurrent=3)` em `start()`.
- Registra os 6 agentes iniciais (`Developer`, `Research`, `Security`, `QA`,
  `Database`, `Architecture`).
- `shutdown()` limpa `self.agent_orchestrator`.

`ultron_2_0/orchestrator_bridge.py`:

- `status()["agents"]` expõe snapshot completo do multiagente (sem credenciais).

## 9. Testes

`tests/test_agents.py` — 19 testes com agentes reais (adaptadores, sem modelos
de IA fictícios):

1. Registro e descoberta de agentes (`AgentRegistry`, `find_by_capability`,
   `select_for_task`).
2. Agente não encontrado não quebra o orquestrador.
3. Execução de tarefa com resultado estruturado e identificação de origem.
4. Ciclo de vida: `pending → assigned → running → review → completed`.
5. Validação rejeita resultado sem origem, sem sumário, arquivos fora do escopo.
6. Validação aceita resultado bem-sucedido completo.
7. Falha de agente registrada e replanejada (tentativas).
8. Falha persistente marca `failed` após `max_attempts`.
9. Concorrência: duas tarefas no mesmo arquivo não rodam conjuntas (isolamento).
10. Status sem expor credenciais (`secret_leak` equivalente).
11. Capacidades dos 6 agentes iniciais (`Developer`, `Research`, `Security`, `QA`).
12. `ResultManager` armazena e valida.
13. `ExecutionMonitor` registra eventos.
14. `AgentOrchestrator` disponível no `UltronCoreRuntime` (6 agentes registrados).
15. `OrchestratorBridge.status()["agents"]` expõe o multiagente sem credenciais.

Resultados registrados: **196 passed** (ULTRON 2.0), **64 passed** (regressão lain).

## 10. Limitações conhecidas

- Agentes iniciais são adaptadores síncronos sobre ferramentas existentes;
  agentes externos reais (OpenCode, Claude Code) ficam para a Fase 5.
- Não há agendador automático de tarefas; `run_ready()` é chamado
  explicitamente (ou por agentes externos na Fase 5).
- Agentes não modificam diretamente a memória canônica (requer autorização,
  Fase 2).
- Resultados de agentes são dados não confiáveis até passar pelo `AgentValidator`.

## 11. Próximas etapas

- Fase 5 — Integração com agentes CLI (OpenCode, Claude Code) e servidores MCP.
- Fase 6 — Evolução da memória (embeddings opcionais, busca semântica).
- Fase 7 — Autonomia operacional (`Planner`, `WorkflowEngine`, `Scheduler`).
- Fase 8 — Validação e estabilização (`docs/roadmap/ULTRON_21_FINAL_REPORT.md`).
