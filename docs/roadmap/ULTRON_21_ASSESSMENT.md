# ULTRON 2.1 — AVALIAÇÃO DA FASE 0 (REAVALIAÇÃO DO PROJETO)

**Data:** 2026-11-11
**Branch:** `integration/etapa-0-fundacao`
**Commit de referência:** `2ed1005` (árvore limpa)
**Ambiente:** Linux, Python 3.12 (`.venv` dedicado), ~4 GB RAM, sem GPU
**Escopo:** reavaliar o estado real após a integração 0–10 e preparar as fases 1–8
do `AGENTS.md` 2.1 e a Fase 2.5 do `INTERFACE.md`.

> Documento de avaliação. Não declara nenhuma fase nova concluída. Toda
> classificação abaixo tem evidência em código, teste ou comando executado.

---

## 1. Método

1. Leitura integral de `AGENTS.md` (2.1), `INTERFACE.md`, `CONTEXT.md` e
   `MEMORY.md` na raiz.
2. Leitura de `PROJECT_CONTEXT.md`, `docs/context/CONTEXT_INDEX.md`,
   `docs/context/DEVELOPMENT_STATE.md`, `docs/ARCHITECTURE.md`,
   `docs/TESTING.md`, `docs/INTEGRATION_AUDIT.md` e dos 9 documentos de
   `docs/memory/`.
3. Inspeção do código real de `ultron-2.0/ultron_2_0/` (3.191 linhas Python):
   `core_runtime`, `orchestrator_bridge`, `tool_contracts`, `tool_gateway`,
   `tool_loop`, `memory_engine`, `memory_injection`, `memory_tools`,
   `marklvi_actions`, `cli`, `voice/*`, `web/*`.
4. Inspeção da interface original do Mark-LVI (inventário para a Fase 2.5):
   `ui.py` (7.504 linhas, PyQt6), `core/avatar.py` (715),
   `core/avatar_mesh.py` (351), `core/viseme.py` (275),
   `core/wake_word.py` (211), `core/hotkey.py` (173),
   `dashboard/server.py` (1.312), `core/confirm.py` (161).
5. Execução das suítes e verificação de integridade dos originais.

## 2. Evidências coletadas

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte ULTRON 2.0 | `ultron-2.0: .venv/bin/python -m pytest -q` | **109 passed** |
| Regressão Lain | `lain: .venv/bin/python -m pytest -q` | **64 passed** |
| Git do produto | `git status --porcelain` | árvore limpa, HEAD `2ed1005` |
| Integridade do banco original | `select count(*)` em `lain/ultron.db` | **12 conversas / 48 mensagens** |
| `Mark-LVI-main/memory/long_term.json` | `ls` | **ausente** (não criado) |
| `Mark-LVI-main/config/api_keys.json` | `ls` | **ausente** (não criado) |

Nenhuma credencial foi lida ou impressa nesta avaliação.

## 3. Arquitetura real (fato de código)

```text
CLI / HUD web / VoicePipeline
        |
        v
OrchestratorBridge.process_text        (ultron_2_0/orchestrator_bridge.py)
        |
        v
Orchestrator do lain (inalterado)      -> ContextManager, PromptEngine, histórico
        |
        v
ProviderRegistry do lain
        |
        v
MemoryInjectionProvider (1x/turno)     (ultron_2_0/memory_injection.py)
        |
        v
ToolCallingProvider (até 4 rodadas)    (ultron_2_0/tool_loop.py)
        |
        v
ToolGateway (allowlist, contrato, timeout)  (ultron_2_0/tool_gateway.py)
        |
        v
Actions do Mark-LVI em worker thread   (ultron_2_0/marklvi_actions.py, memory_tools.py)
```

- Banco isolado: `ultron-2.0/data/ultron2.db` (SQLite).
- Memória canônica: `data/memory.json`, `data/memory_records.json`,
  `data/memory_history.json` (motor `MemoryEngine`).
- Interfaces usam o mesmo `process_text` (CLI, HUD, voz) — não há segundo
  orquestrador.

## 4. Inventário e estado real dos componentes

| Componente | Estado | Evidência |
|---|---|---|
| Núcleo por composição (Orchestrator do lain) | `IMPLEMENTED` | `core_runtime.start` |
| Histórico único persistente | `IMPLEMENTED` | `test_bridge.py` |
| ProviderRegistry (mock + gemini) | `IMPLEMENTED` | `core_runtime.py` |
| Tool calling + ToolGateway | `IMPLEMENTED` | `tool_loop.py`, `tool_gateway.py` |
| 4 ferramentas operacionais + 3 de memória | `IMPLEMENTED` | `marklvi_actions.py`, `memory_tools.py` |
| Confirmação de ação sensível | `PARTIAL` | contrato existe; gateway **recusa** `forget` |
| Memória tipada/versionada/injeção | `IMPLEMENTED` | `memory_engine.py` (1.173 linhas), 17 testes |
| STT / TTS / reprodução | `IMPLEMENTED` | `voice/*`, TTS validado ao vivo |
| Voz reusando o núcleo | `IMPLEMENTED` | `test_voice_pipeline.py` |
| HUD web | `IMPLEMENTED` (mínimo funcional) | 154 linhas de API + `index.html` de 420 linhas |
| Wake word / VAD / barge-in | `PLANNED` | sem código no 2.0 |
| Model Router | `PLANNED` | não existe |
| Sistema multiagente | `PLANNED` | não existe |
| Integração CLI/MCP | `PLANNED` | não existe |
| Embeddings / busca semântica | `PLANNED` | não existe |
| Criptografia / backup da memória | `PLANNED` | não existe |
| Planner / WorkflowEngine | `PLANNED` | não existe |
| Documentação da raiz no Git | `BLOCKED` | `docs/` e specs da raiz fora de repositório |

## 5. Lacunas por fase do `AGENTS.md` 2.1

### Fase 0 — Reavaliação
- **Este documento.** Concluída com a entrega deste arquivo.

### Fase 1 — Documentação e controle de versão
- `docs/`, `AGENTS.md`, `CONTEXT.md`, `MEMORY.md`, `INTERFACE.md` e
  `PROJECT_CONTEXT.md` **não estão sob Git** (só `ultron-2.0/` e `lain/` são
  repositórios).
- `docs/context/CONTEXT_INDEX.md` cobre a documentação antiga, mas não as
  specs da raiz (`INTERFACE.md`) nem o novo diretório `docs/roadmap/`.
- Links internos só são validados para `PROJECT_CONTEXT.md` e `docs/memory/`
  (`tests/test_docs.py`); não há verificação global.

### Fase 2 — Autorização interativa
- **Não existe** `AuthorizationManager`, `PendingAction` ou `ApprovalToken`.
- `ToolContract.requires_confirmation` existe, mas `ToolGateway.execute`
  **recusa sempre** (`tool_gateway.py:155-163`). `forget` é inutilizável na
  prática.
- Não há confirmação pela CLI nem pelo HUD, nem prevenção de replay/expiração.

### Fase 2.5 — Interface (`INTERFACE.md`)
- HUD atual tem chat, status, ferramentas, histórico e troca de provider.
- **Não tem**: controles de voz no HUD, painéis de configuração, indicadores
  de captura/processamento em tempo real, animações, temas/tokens
  centralizados, estados de carregamento/erro ricos, responsividade além de um
  breakpoint.
- A referência Mark-LVI é **PyQt6** (`ui.py`, avatar, viseme, wake word) e um
  dashboard HTTPS com pareamento. Portar PyQt6 conflita com o ambiente
  (~4 GB RAM, sem GPU) e com a decisão anterior de HUD web.

### Fase 3 — Model Router
- Não existe `ModelRouter`, `ProviderAdapter`, `ModelRegistry`,
  `ModelCapabilities`, `ModelSelectionPolicy`, `FallbackManager`,
  `RetryManager` ou métricas.
- O núcleo depende do `ProviderRegistry` do lain com seleção manual por id.

### Fase 4 — Sistema multiagente
- Não existe `AgentOrchestrator`, `AgentRegistry`, `AgentExecutor`,
  `AgentTask`, `TaskQueue`, `ResultManager`, `AgentValidator` ou
  `ExecutionMonitor`.

### Fase 5 — Agentes CLI e MCP
- Não existe adaptador para OpenCode, Claude Code ou servidores MCP.

### Fase 6 — Evolução da memória
- Recuperação lexical existe; embeddings, busca híbrida, relações,
  criptografia em repouso e backup/restauração **não existem**.

### Fase 7 — Autonomia operacional
- Não existe `Planner`, `TaskDecomposer`, `WorkflowEngine`, `Scheduler`,
  `RecoveryManager` ou `StateTracker`.

### Fase 8 — Validação e estabilização
- Baseline atual: 109 + 64 testes. Sem testes de autorização, roteamento,
  agentes, MCP, backup ou UI além do HUD mínimo.

## 6. Riscos e incompatibilidades

| # | Risco | Impacto | Mitigação proposta |
|---|---|---|---|
| R1 | Documentação fora do Git | perda de contexto entre sessões/agentes | Fase 1: repositório na raiz com `.gitignore` para os projetos originais |
| R2 | `asyncio.wait_for` não interrompe thread já iniciada | tool continua após timeout | manter timeout + auditoria; documentar limite (já em `SECURITY.md`) |
| R3 | Confirmação bloqueante no meio do turno | deadlock em HUD/voz | separar `PendingAction` da execução; token de uso único |
| R4 | PyQt6 do Mark-LVI | RAM/dependências incompatíveis | Fase 2.5: adaptar funcionalidades ao HUD web, documentando a decisão |
| R5 | Model Router com um único provider real | roteador fictício | só implementar com ≥2 providers testáveis (mock conta como provider de teste) |
| R6 | Agentes externos com acesso local | execução não autorizada | adaptadores com allowlist, timeout, diretório de trabalho isolado e auditoria |
| R7 | Credenciais em prompts/logs | vazamento | nenhuma credencial em task/descrição; mascaramento já existente |
| R8 | Memória sem criptografia/backup | perda/corrupção | Fase 6; manter backup manual documentado até lá |
| R9 | HUD exposto à rede | acesso indevido | bind `127.0.0.1` por padrão; sem TLS → não expor |

## 7. Plano de execução priorizado

| Ordem | Fase | Entrega | Critério de aceite |
|---|---|---|---|
| 1 | 1 | docs da raiz versionados + índice unificado + verificação de links | `git log` na raiz; teste de links global |
| 2 | 2 | `AuthorizationManager` + CLI + HUD + testes de replay/expiração | `forget` executável só após aprovação |
| 3 | 2.5 | auditoria + HUD ULTRON com paridade funcional | matriz de funcionalidades + testes |
| 4 | 3 | Model Router com ≥2 providers + fallback | testes de seleção/fallback |
| 5 | 4 | multiagente com contratos e isolamento | testes de concorrência |
| 6 | 5 | 1 integração CLI + 1 MCP | testes com timeout |
| 7 | 6 | embeddings opcionais + backup/restauração | testes de compatibilidade |
| 8 | 7 | workflows com estado e recuperação | testes de replanejamento |
| 9 | 8 | validação final + relatório | suíte completa + `ULTRON_21_FINAL_REPORT.md` |

## 8. Critérios de conclusão (gerais)

Uma fase só será declarada concluída com: implementação, contratos, testes
executados, resultados registrados, regressões verificadas, documentação
atualizada, limitações e riscos avaliados — conforme §10 do `AGENTS.md` 2.1.

## 9. Limitações que dependem de terceiros

- STT Live e TTS ao vivo dependem de rede/quota/microfone.
- Não há GPU; modelos locais grandes estão fora de escopo.
- Integrações com OpenCode/Claude Code/MCP dependem dos binários/servidores
  instalados; serão validadas apenas se disponíveis localmente.
- Nenhuma credencial será criada, copiada ou impressa.

## 10. Conclusão da Fase 0

O estado real confirma a conclusão da integração 0–10 (109 + 64 testes,
originais intactos). As fases 2–8 do 2.1 e a Fase 2.5 da interface **não estão
implementadas** e passam a ser o roteiro de trabalho. A Fase 1 é a primeira
prioridade por sustentar todas as demais.
