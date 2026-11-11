# INTEGRACOES — Integrações Externas do ULTRON 2.1 (Fase 5)

> **Status:** IMPLEMENTADO (Fase 5 concluída). Ver `docs/context/TECHNICAL_DECISIONS.md`
> (ADR-016), `tests/test_integrations.py` (19 testes) e
> `docs/roadmap/ULTRON_21_PHASE5_REPORT.md`.

## 1. Objetivo

Conectar o ULTRON a agentes/servidores externos (OpenCode CLI, servidores MCP)
por meio de adaptadores independentes, processos isolados com timeout e controle
de permissões por integração — sem perder o controle central do fluxo de execução
(AGENTS.md §4.4, §5.3).

O `IntegrationOrchestrator` não é um segundo orquestrador conversacional: não
toca no histórico de conversa, nem na memória canônica, nem no caminho único
`process_text`. Apenas encaminha tarefas especializadas a agentes/servidores
externos e devolve resultados para avaliação do ULTRON.

## 2. Arquitetura do pacote `integrations/`

```
ultron_2_0/integrations/
├── __init__.py            # API pública
├── contracts.py           # IntegrationTask, IntegrationResult, IntegrationType,
│                          # IntegrationState, IntegrationCapability, new_task_id
├── base.py                # ExternalIntegration (subprocesso isolado, timeout,
│                          # sanitize_output)
├── cli_adapter.py         # OpenCodeAdapter (opencode run)
├── mcp_adapter.py         # MCPAdapter (opencode mcp list)
├── integration_registry.py  # IntegrationRegistry (registro, habilitar/desabilitar)
└── integration_orchestrator.py  # IntegrationOrchestrator (coordena tarefas)
```

## 3. Contratos de dados (`contracts.py`)

### `IntegrationType`
- `cli` — agente CLI (OpenCode, Claude Code)
- `mcp` — servidor MCP (Model Context Protocol)

### `IntegrationState` — estados da tarefa
`pending → running → completed / failed / cancelled / disabled`

### `IntegrationTask`
Tarefa delegada a uma integração externa: identificador, tipo, alvo (ex:
`opencode`, `mcp:filesystem`), prompt, parâmetros, estado, resultado, erro,
tentativas e timestamps.

### `IntegrationResult`
Resultado estruturado com identificação de origem (`integration_type`, `target`),
`task_id`, sucesso/falha, conteúdo, sumário, erro, saída bruta sanitizada e
tempo de execução.

## 4. Componentes

| Módulo | Classe | Responsabilidade |
|---|---|---|
| `integration_orchestrator.py` | `IntegrationOrchestrator` | Cria tarefas, executa via adaptador, isola falhas, ciclo de vida |
| `integration_registry.py` | `IntegrationRegistry` | Registro, listar, habilitar/desabilitar individualmente por target |
| `base.py` | `ExternalIntegration` | Subprocesso isolado (`create_subprocess_exec`, sem shell=True), timeout (`asyncio.wait_for`), parse de saída, `sanitize_output` |
| `cli_adapter.py` | `OpenCodeAdapter` | Adaptador OpenCode sobre `opencode run [--format json] [--session] [--model] [--agent] [--auto] <mensagem>` |
| `mcp_adapter.py` | `MCPAdapter` | Adaptador MCP sobre `opencode mcp list` |

## 5. Interface real confirmada (OpenCode CLI)

O adaptador CLI usa exatamente a interface exposta pelo OpenCode instalado
(`/home/marcelo/.opencode/bin/opencode`):

```
opencode run [--session ID] [--model MODEL] [--agent AGENT]
             [--auto] [--format json] <mensagem>
opencode mcp list        # lista servidores MCP configurados e status
opencode mcp add         # adiciona um servidor MCP
opencode mcp auth        # autentica em servidor MCP OAuth remoto
```

Não são inventados comandos, APIs ou contratos.

## 6. Regras de projeto (AGENTS.md §4.4, §5.3)

1. **Inspecionar interfaces reais** — nada inventado.
2. **Adaptadores independentes** — uma por integração.
3. **Processos externos isolados** — subprocesso, nunca `shell=True`.
4. **Limites de execução** — timeout por integração (`asyncio.wait_for`).
5. **Registrar tarefas e resultados** — `IntegrationTask`/`IntegrationResult`.
6. **Controle de permissões por integração** — habilitar/desabilitar individual.
7. **Desativar individualmente** — cada integração pode ser ligada/desligada.
8. **Resultados não confiáveis** — dados externos validados antes de usar (não
   aplicados automaticamente à memória canônica nem tratados como instruções).

## 7. Fluxo de execução de uma tarefa de integração

```text
create_task(integration_type, target, prompt)
  → IntegrationTask (estado: pending)
  → run_task()
     → IntegrationRegistry.get(target)
        → verifica habilitada
           → ExternalIntegration.run(task)
              → create_subprocess_exec (sem shell=True)
                 → asyncio.wait_for (timeout)
                 → captura stdout/stderr
                 → sanitize_output (remove segredos)
                 → parse_output (JSON ou texto bruto)
              → IntegrationResult (sucesso/falha)
     → task estado: completed / failed / disabled
```

Falhas (timeout, comando não encontrado, código de saída não-zero, exceção)
são tratadas de forma controlada e não comprometem o núcleo ULTRON.

## 8. Integração no núcleo

`ultron_2_0/core_runtime.py`:

- Cria `IntegrationOrchestrator()` em `start()`.
- Registra `OpenCodeAdapter()` e `MCPAdapter()`.
- `shutdown()` limpa `self.integration_orchestrator`.

`ultron_2_0/orchestrator_bridge.py`:

- `status()["integrations"]` expõe snapshot completo das integrações
  (sem credenciais).

## 9. Testes

`tests/test_integrations.py` — 19 testes (sem exigir chave de API nem servidor
MCP real):

1. `OpenCodeAdapter.build_command` monta o comando real do OpenCode
   (`--format json`, `--session`, `--model`, `--agent`, `--auto`).
2. `parse_output` parseia saída JSON e texto bruto.
3. Sanitização de segredos na saída (`AIza`, `sk-`, `API_KEY=`, tokens longos).
4. Integração desabilitada não executa (erro controlado).
5. Comando não encontrado trata erro sem derrubar o núcleo.
6. Timeout tratado de forma controlado.
7. `IntegrationRegistry`: registro, listar, habilitar/desabilitar individual.
8. `IntegrationOrchestrator`: cria tarefa, executa, integração não registrada,
   integração desabilitada.
9. Status sem expor credenciais.
10. `MCPAdapter` lista servidores via `opencode mcp list`.
11. `IntegrationOrchestrator` disponível no `UltronCoreRuntime` (OpenCode + MCP
    registrados).
12. `OrchestratorBridge.status()["integrations"]` expõe as integrações sem
    credenciais.

Resultados registrados: **215 passed** (ULTRON 2.0), **64 passed** (regressão lain).

## 10. Limitações conhecidas

- Nenhum servidor MCP real configurado neste ambiente; o `MCPAdapter` lista
  servidores via `opencode mcp list` e reporta de forma controlada quando
  nenhum está acessível. Execução de tarefa MCP real (stdio/HTTP) requer um
  servidor MCP ativo.
- Agentes CLI externos reais (OpenCode com chave de API, Claude Code) exigem
  configuração e rede; os testes exercitam os caminhos de código sem chamada
  real.
- Não há agendador automático de tarefas de integração; `run_task()`/`run_ready()`
  são chamados explicitamente.

## 11. Próximas etapas

- Fase 6 — Evolução da memória (embeddings opcionais, busca semântica,
  recuperação híbrida, criptografia em repouso, backup/restauração).
- Fase 7 — Autonomia operacional (`Planner`, `TaskDecomposer`,
  `WorkflowEngine`, `Scheduler`, `RecoveryManager`, `StateTracker`).
- Fase 8 — Validação e estabilização (`docs/roadmap/ULTRON_21_FINAL_REPORT.md`).
