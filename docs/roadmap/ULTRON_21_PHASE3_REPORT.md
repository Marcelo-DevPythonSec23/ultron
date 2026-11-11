# ULTRON_21_PHASE3_REPORT — Fase 3: Model Router

> **Data:** 2026-11-11  
> **Fase:** 3 — Model Router (conforme `AGENTS.md` §4)  
> **Status:** CONCLUÍDA com evidências verificáveis.

---

## A. Objetivo da fase

Permitir que o ULTRON selecione e coordene diferentes provedores de modelo de IA,
escolhendo o modelo conforme o tipo de tarefa, com fallback, timeout e retry com
backoff — sem criar um segundo orquestrador conversacional nem expor credenciais.

Critérios de conclusão (`AGENTS.md` §4):

- [x] Pelo menos dois provedores integrados e efetivamente testados (`mock` + `gemini` via `StubProvider` em testes; `mock`/`gemini` reais em produção).
- [x] Seleção de modelo validada (política determinística por `TaskType`, overrides explícitos por tarefa).
- [x] Fallback testado (entre provedores, opt-in; `mock` nunca automático).
- [x] Falhas de provedores isoladas (cooldown por provedor, última exceção sem embrulho).
- [x] Timeout e retry com backoff (exponencial limitado, classificação transitório vs definitivo).
- [x] Configurações e credenciais protegidas (`sanitize_error`, snapshot sem segredos, `secret_leak: False`).
- [x] `ProviderRegistry` existente preservado (autoridade de registro, duck typing).

---

## B. Auditoria da implementação anterior

Antes da Fase 3, o roteamento era manual: o `Orchestrator` do lain usava
`request.provider or registry.default_provider_id` e `request.model or
provider.default_model` diretamente, sem seleção por tipo de tarefa, sem
fallback, sem timeout/retry estruturado. O `ProviderRegistry` continuava como
autoridade; nada foi removido.

ADR-010 ("Nenhum Model Router fictício") estava como `Aceita` com roteamento
automático `PLANNED`. A Fase 3 substitui ADR-010 por ADR-014 (Aceita), que
implementa o roteador real.

## C. Arquitetura implementada

O `ModelRouter` envolve o `ProviderRegistry` do lain e é passado ao
`Orchestrator` como `provider_registry` (duck typing). Componentes:

| Módulo | Classe/Elemento | Responsabilidade |
|---|---|---|
| `router.py` | `ModelRouter`, `RouterConfig`, `RoutingProvider`, `AUTO_MODEL` | Orquestração do roteamento, modo `primary`/`auto`, facade observável |
| `capabilities.py` | `TaskType`, `ModelCapabilities`, `infer_task_type` | Tipos de tarefa, capacidades, heurística sem modelo |
| `catalog.py` | `ModelCatalog`, `build_catalog` | Catálogo derivado do registry, overrides explícitos por tarefa |
| `policy.py` | `ModelSelectionPolicy`, `Candidate` | Ranking determinístico por aderência à tarefa |
| `retry.py` | `RetryPolicy`, `RetryManager` | Backoff exponencial, classificação de erros, exceção sem embrulho |
| `fallback.py` | `FallbackManager` | Tentativa ordenada de candidatos, isolamento de falhas |
| `metrics.py` | `MetricsRegistry`, `sanitize_error` | Contadores, cooldown, remoção de segredos |
| `adapters.py` | `ProviderAdapter` | Timeout por chamada, stream até 1º chunk |

Fluxo: `infer_task_type` → `policy.rank` → `ProviderAdapter` (timeout) →
`FallbackManager` + `RetryManager` → provedor real.

## D. Arquivos criados, modificados e removidos

### Criados (código)

- `ultron-2.0/ultron_2_0/routing/__init__.py`
- `ultron-2.0/ultron_2_0/routing/router.py`
- `ultron-2.0/ultron_2_0/routing/capabilities.py`
- `ultron-2.0/ultron_2_0/routing/catalog.py`
- `ultron-2.0/ultron_2_0/routing/policy.py`
- `ultron-2.0/ultron_2_0/routing/retry.py`
- `ultron-2.0/ultron_2_0/routing/fallback.py`
- `ultron-2.0/ultron_2_0/routing/metrics.py`
- `ultron-2.0/ultron_2_0/routing/adapters.py`

### Criados (testes)

- `ultron-2.0/tests/test_routing.py` (41 testes)

### Criados (documentação, raiz do projeto)

- `docs/MODEL_ROUTER.md`
- `docs/roadmap/ULTRON_21_PHASE3_REPORT.md` (este arquivo)

### Modificados (código)

- `ultron-2.0/ultron_2_0/core_runtime.py` — atributo `router`, `Orchestrator(provider_registry=self.router)`, `register_provider` delega ao router, `shutdown` limpa
- `ultron-2.0/ultron_2_0/orchestrator_bridge.py` — `router_config`, `status()["router"]`
- `ultron-2.0/ultron_2_0/cli.py` — `/status` mostra roteador e falhas
- `ultron-2.0/tests/fakes.py` — `StubProvider` (provider_id próprio, falhas, delay, streaming)

### Modificados (documentação, raiz do projeto)

- `docs/context/TECHNICAL_DECISIONS.md` — ADR-010 substituída por ADR-014 (Model Router)
- `docs/context/MODULE_MAP.md` — seção 6: roteamento de modelos (Fase 3)
- `docs/context/DEVELOPMENT_STATE.md` — Fase 3 de `PLANNED` → `IMPLEMENTED`; contagem de testes 136 → 177
- `PROJECT_CONTEXT.md` — Model Router de `PLANNED` → `IMPLEMENTED`
- `docs/ARCHITECTURE.md` — ModelRouter no diagrama de autoridade e fluxo de texto; seção 3.3a
- `docs/TESTING.md` — contagem 136 → 177; tabela de cobertura com test_routing.py; resultados; mapeamento Fase 3
- `docs/context/CONTEXT_INDEX.md` — referência a docs/MODEL_ROUTER.md

### Removidos

- (nenhum)

## E. Dependências adicionadas

Nenhuma dependência nova. Reutiliza: `google-genai>=3,<4` (via lain), `asyncio`,
`dataclasses`, `json`, `re`, `time`, `collections.deque` — todos da stdlib.

## F. Testes executados e resultados

| Suíte | Resultado | Data |
|---|---|---|
| `ultron-2.0/tests/` (incl. `test_routing.py` 41) | **177 passed** | 2026-11-11 |
| `lain/tests/` (regressão) | **64 passed** | 2026-11-11 |

Testes da Fase 3 (`tests/test_routing.py`, 41):

1. Inferência determinística de tipo de tarefa (chat/code/reasoning/long_context/cheap) — 5 testes parametrizados + override explícito + prioridade de contexto longo.
2. Catálogo/capacidades e ranking da política — pontuação por tarefa, ordenação, exclusão, bônus ao provedor preferido.
3. Override de modelo por tarefa (`model_overrides`) — decisão explícita, não empate de score.
4. Retry com backoff exponencial limitado `[0.1, 0.2, 0.4, 0.5]`.
5. Classificação de erros: transitórios repetíveis, definitivos não repetíveis, desconhecidos repetíveis.
6. Retry repete transitório antes de responder; autenticação não é repetida mas permite fallback.
7. Métricas: cooldown, sanitização de segredo (`AIza` → `[redacted]`), tamanho limitado a 300 chars.
8. Status do roteador não expõe segredos (`secret_leak: False`).
9. Provedor padrão continua primário (fallback desligado = erro propagado, sem tentativa no secundário).
10. Fallback troca de provedor após falha; métricas atualizadas; decisão registrada.
11. Timeout isola provedor e permite fallback; cooldown marca indisponível.
12. Provedor em cooldown é pulado no fallback.
13. `mock` nunca é fallback automático (default); com `allow_mock_fallback=true` é usado.
14. Provedor explícito desliga fallback.
15. Modelo explícito é respeitado e desliga fallback.
16. Identidade do `RoutingProvider` vem do registry (`provider_id`, `default_model`).
17. Streaming: failover antes do primeiro chunk; não depois de saída parcial; `generate_response_streaming` devolve identidade real.
18. Configuração por env: todos os valores, sanitização de `GEMINI_API_KEY`, tolera valores inválidos, rejeita parâmetros inválidos.
19. Modo `auto`: `default_model` retorna `"auto"` sem provedor explícito; seleção por tipo de tarefa; respeito a provedor/modelo explícitos; modos inválidos rejeitados; env `ULTRON_ROUTER_MODE`.
20. Integração real pelo `OrchestratorBridge`: fallback, provedor real persistido na conversa, status do roteador, sem vazamento de segredo.

Suítes anteriores verificadas sem regressão: 177 (2.0) + 64 (lain).

## G. Verificações de segurança

- `lain/` e `Mark-LVI-main/` **não modificados** (verificado via `git status`).
- `GEMINI_API_KEY` nunca impressa, logada ou duplicada (validado com `json.dumps` sobre `status()` e `to_public_dict()`).
- `sanitize_error` remove padrões `AIza...`, `sk-...`, `*KEY=...`, `*TOKEN=...`, `*SECRET=...`, `*PASSWORD=...`.
- `Mark-LVI-main/config/api_keys.json` não criado nem editado.
- `lain/ultron.db` e `Mark-LVI-main/memory/long_term.json` não tocados.
- Todas as ferramentas passam pelo `ToolGateway` (allowlist, validação, timeout, autorização).
- O `ModelRouter` não é um segundo orquestrador; não cria histórico paralelo nem memória independente.
- Resultado de provedor nunca tratado como instrução executável.

## H. Limitações e funcionalidades pendentes

- Busca semântica/embeddings não fazem parte do roteador (Fase 6).
- Cooldown e pendências de autorização vivem em memória (reiniciar descarta).
- Não há agendador automático de `expire()`/`consolidate()` (operações de API).
- Provedores reais (Gemini) exigem rede e `GEMINI_API_KEY`; testes usam stubs locais (`StubProvider`).
- `mode="auto"` é opt-in; o padrão continua `primary` para não trocar custo/privacidade silenciosamente.
- Nenhum teste ao vivo automatizado de STT Live (rede/microfone) — pré-existente.

## I. Próximas etapas recomendadas

1. Fase 4 — Sistema Multiagente (`AgentOrchestrator`, `AgentRegistry`, `AgentExecutor`,
   `AgentTask`, `TaskQueue`, `AgentCommunication`, `ResultManager`, `AgentValidator`,
   `ExecutionMonitor`). Agentes iniciais: Developer, Research, Security, QA, Database,
   Architecture.
2. Fase 5 — Integração com agentes CLI (OpenCode, Claude Code) e servidores MCP.
3. Fase 6 — Evolução da memória: embeddings opcionais, busca semântica, recuperação
   híbrida, criptografia em repouso, backup/restauração.
4. Fase 7 — Autonomia operacional: `Planner`, `TaskDecomposer`, `WorkflowEngine`,
   `Scheduler`, `RecoveryManager`, `StateTracker`.
5. Fase 8 — Validação e estabilização: `docs/roadmap/ULTRON_21_FINAL_REPORT.md`.

## J. Estado do Git e commits

Repositório do produto (`ultron-2.0/`): HEAD `e837705` (fase 2.5). Alterações da Fase 3
não commitadas até este relatório.

Repositório da raiz (`/home/marcelo/projetos/ultron/`): HEAD `ae28beb` (fase 2.5).
Documentação da Fase 3 não commitada até este relatório.

**Próximo passo:** commit do produto (`ultron-2.0/`) e da raiz, verificando árvores
limpas, sem tocar em `lain/` nem `Mark-LVI-main/`.
