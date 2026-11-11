# AUTONOMIA — Autonomia Operacional do ULTRON 2.1 (Fase 7)

> **Status:** IMPLEMENTADO (Fase 7 concluída). Ver `docs/context/TECHNICAL_DECISIONS.md`
> (ADR-018), `tests/test_autonomy.py` (21 testes) e
> `docs/roadmap/ULTRON_21_PHASE7_REPORT.md`.

## 1. Objetivo

Permitir que o ULTRON planeje e execute fluxos de trabalho complexos, sem
criar um segundo orquestrador conversacional (AGENTS.md §4.7).

O `WorkflowEngine` recebe objetivos complexos, os decompõe em tarefas via
`Planner`/`TaskDecomposer`, distribui execução ao `AgentOrchestrator` (Fase 4)
ou `IntegrationOrchestrator` (Fase 5), monitora via `ExecutionMonitor` e
gerencia persistência de estado via `StateTracker`.

## 2. Arquitetura do pacote `autonomy/`

```
ultron_2_0/autonomy/
├── __init__.py            # API pública
├── contracts.py           # Workflow, WorkflowStep, WorkflowState,
│                          # StepState, StepDependency, new_workflow_id,
│                          # new_step_id
├── planner.py             # Planner — cria Workflow a partir de um objetivo
├── task_decomposer.py     # TaskDecomposer — decomposicao deterministica
├── workflow_engine.py     # WorkflowEngine — execucao de workflows
├── state_tracker.py       # StateTracker — persisticao de estado
├── scheduler.py           # Scheduler — agendamento por horario
└── recovery_manager.py    # RecoveryManager — recuperacao apos falhas
```

## 3. Contratos de dados (`contracts.py`)

### `WorkflowState` — estados do workflow
`pending → running → completed / failed / cancelled / paused`

### `StepState` — estados de um passo
`pending → assigned → running → review → completed / failed / cancelled / skipped`

### `Workflow`
Objetivo decomposto em passos, com limites de segurança:
- `max_steps` — número máximo de passos
- `max_execution_seconds` — tempo máximo de execução
- `require_human_approval` — exigir aprovação humana

### `WorkflowStep`
Um passo executável: objetivo, descrição, alvo (agente ou integração),
tipo do alvo, contexto, dependências, permissões, tentativas, estado,
resultado e erro.

## 4. Componentes

| Módulo | Classe | Responsabilidade |
|---|---|---|
| `planner.py` | `Planner` | Cria Workflow a partir de objetivo, com limites de segurança |
| `task_decomposer.py` | `TaskDecomposer` | Decomposição determinística de objetivo em passos |
| `workflow_engine.py` | `WorkflowEngine` | Executa workflows distribuindo passos aos orquestradores |
| `state_tracker.py` | `StateTracker` | Persiste estado de workflows para recuperação após falhas |
| `scheduler.py` | `Scheduler` | Agenda workflows por horário de execução |
| `recovery_manager.py` | `RecoveryManager` | Plana recuperação de workflows FAILED/PAUSED |

## 5. Regras de projeto (AGENTS.md §4.7)

1. **Separar planejamento de execução** — o Planner apenas planeja, o Engine executa.
2. **Limites de recursos e tempo** — `max_steps`, `max_execution_seconds`.
3. **Autorização para ações sensíveis** — `require_human_approval`.
4. **Registrar decisões e resultados** — StateTracker, ExecutionMonitor.
5. **Evitar loops de execução** — dependências lineares, estados bem definidos.
6. **Limites de tentativas por passo** — `max_attempts`.
7. **Preservar interrupção humana** — estado `PAUSED`, retry/skip de passo.

## 6. Fluxo de execução de um workflow

```text
Planner.plan(objetivo)
  → TaskDecomposer.decompose()  (passos com dependências lineares)
     → Workflow (estado: pending)
     → StateTracker.register()  (persiste estado)
     → WorkflowEngine.run()
        → para cada passo com dependências satisfeitas:
           → AgentOrchestrator.create_task()  (Fase 4)
              ou IntegrationOrchestrator.create_task()  (Fase 5)
           → aguarda conclusão (polling)
           → passo: completed / failed (com retry até max_attempts)
        → workflow: completed (todos sucesso) / failed (algum falhou)
```

Falhas de passo não derivam em falha imediata do workflow se houver tentativas
restantes. O `RecoveryManager` pode replanejar passos falhados ou retomar
workflows pausados.

## 7. Integração no núcleo

`ultron_2_0/core_runtime.py`:

- Cria `WorkflowEngine` (opcional, com AgentOrchestrator e
  IntegrationOrchestrator) em `start()`.
- `shutdown()` limpa o engine.

`ultron_2_0/orchestrator_bridge.py`:

- Expor estado de autonomia (workflows, agendamentos, recuperação) via
  `status()`.

## 8. Testes

`tests/test_autonomy.py` — 21 testes (sem exigir execução real de
agentes/integrações):

1. Decomposição determinística de objetivo (mesmo objetivo => mesmos passos).
2. Decomposição por palavra-chave (developer, research, security, qa,
   database, architecture, opencode).
3. Fallback quando nenhuma palavra-chave corresponde.
4. Dependências lineares entre passos (primeiro sem dependência, resto depende
   do anterior).
5. Planner cria Workflow com limites de segurança.
6. Workflow estados: `is_done()`, `all_successful()`, transições de passo.
7. StateTracker: register/get/update/remove/list, persistência em disco,
   carregamento após reinício, status sem credenciais.
8. Scheduler: agenda, `due()` (horário chegou/não chegou), `pending()`,
   `cancel()`.
9. RecoveryManager: lista workflows needing recovery, plano de recuperação,
   retry de passo, pular passo, retomar pausado.
10. WorkflowEngine executa passo com sucesso (agente mock).
11. WorkflowEngine esgotamento de tentativas → workflow falhado.
12. WorkflowEngine sem orquestradores → erro controlado.
13. WorkflowEngine respeita limite de tempo máximo.
14. Status público do engine sem credenciais.

Resultados registrados: **252 passed** (ULTRON 2.0), **64 passed** (regressão lain).

## 9. Limitações conhecidas

- Não há agendador automático de loop; `Scheduler.due()` deve ser chamado por
  um loop externo ou pelo WorkflowEngine.
- A execução real de passos depende dos orquestradores de Fase 4 (agentes) e
  Fase 5 (integrações CLI/MCP) estarem configurados.
- Não há execução de código gerado por modelos (segurança: AGENTS.md §3.3).
- Recuperação após falha é baseada em tentativas configuradas, não em
  replanejamento automático de objetivos inteiros.

## 10. Próximas etapas

- Fase 8 — Validação e estabilização (`docs/roadmap/ULTRON_21_FINAL_REPORT.md`).
