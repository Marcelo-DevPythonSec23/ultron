# ULTRON_21_STARTUP_DIAGNOSTIC — Relatório de Diagnóstico de Inicialização

> **Data:** 2026-11-12
> **Fase:** 9 — Testes e Validação (conforme `AGENTS.md` §4.9)
> **Status:** EM ANDAMENTO

---

## A. Estado Inicial

### Ambiente de Execução
- **Python:** 3.12.3
- **Venv:** `/home/marcelo/projetos/ultron/ultron-2.0/.venv`
- **Pip:** 26.3
- **Git:** repositório `ultron-2.0/` em branch `integration/etapa-0-fundacao`
- **Repositório raiz:** `/home/marcelo/projetos/ultron/` em branch `master`

### Suítes de Teste Existentes

| Suíte | Arquivo | Status Inicial |
|-------|---------|----------------|
| ULTRON 2.0 | `ultron-2.0/tests/` | 264 passed, 1 skipped |
| Regressão Lain | `lain/tests/` | 64 passed |
| Fase 3 — Model Router | `tests/test_routing.py` | Incluído acima |

### Componentes Envolvidos no Fluxo de Roteamento

```text
Usuário
  │
  ▼
Interface (CLI / voz / HUD web)
  │
  ▼
OrchestratorBridge (ultron_2_0/orchestrator_bridge.py)
  │
  ▼
UltronCoreRuntime (ultron_2_0/core_runtime.py)
  │
  ▼
Orchestrator (lain/app/core/orchestrator.py)  ← ÚNICO ciclo de conversa
  │  ├── ChatService
  │  ├── ContextManager
  │  └── ProviderRegistry (autoridade de provedores)
  │        └── ModelRouter (Fase 3: seleção/fallback; NÃO é orquestrador)
  │              └── MemoryInjectionProvider (extensão 2.0)
  │                    └── ToolCallingProvider (extensão 2.0)
  │                          └── ToolGateway (allowlist, validação, timeout, auditoria)
  │                                └── actions do Mark-LVI (worker threads)
```

---

## B. Matriz de Inicialização

| Interface | Comando | Resultado Inicial | Evidência |
|-----------|---------|-----------------|-----------|
| CLI de texto | `.venv/bin/python main.py --cli` | ❌ FALHA (sem provedor válido) | `ProviderConnectionError` |
| CLI de texto (--demo) | `.venv/bin/python main.py --demo` | ❌ FALHA (mesmo motivo) |
| HUD web | `.venv/bin/python -m ultron_2_0.web` | NÃO TESTADO |
| Interface Desktop | `python -m ultron_2_0.interface` | ❌ Não implementada (estágio 2.5 pendente) |
| One-shot | `.venv/bin/python main.py --demo` | ❌ FALHA (mesmo motivo) |

### Problema Identificado

O `ProviderRegistry` do lain possui apenas o provedor `gemini` registrado (via `create_default_registry` em `lain/app/intelligence/providers/registry.py`). O `ModelRouter` envolve este registry, mas:

1. Se `GEMINI_API_KEY` não estiver configurada ou o Gemini estiver indisponível (rate limit, quota excedida), não há fallback automático.
2. O `mock` NÃO é usado como fallback automático (regras do ADR-014).
3. Não há mecanismo de fallback automático entre provedores.

---

## C. Causas Raiz Identificadas

### C1: Provedor Único Sem Fallback

O `ProviderRegistry` do lain registra apenas `mock` (sempre) e `gemini` (se `GEMINI_API_KEY` disponível). Quando o gemini falha (ex: rate limit 429), não há provedor alternativo automático.

**Arquivo:** `lain/app/intelligence/providers/registry.py`
**Linha:** `create_default_registry()` — registra mock e gemini apenas.

### B. Configuração de Fallback Desligada

`RouterConfig.fallback_enabled` padrão é `False`. Mesmo que houvesse múltiplos provedores, o fallback automático não aconteceria sem configuração explícita.

**Arquivo:** `ultron_2_0/ultron_2_0/routing/router.py`
**Linha:** `RouterConfig.__post_init__` e `from_env()`

### C. Nenhuma Classificação de Erros por Provedor

O `RetryManager` classifica erros como transitórios/definitivos, mas não há mecanismo de cooldown por provedor que impeça tentativas repetidas em provedor falho.

### D. Não Há Circuit Breaker

Não há mecanismo para marcar um provedor como "indisponível temporariamente" após N falhas consecutivas.

---

## D. Correções Aplicadas

### 1. ModelRouter — Seleção de Provedor por Tarefa

O `ModelRouter._plan()` já implementa seleção por tipo de tarefa via `ModelSelectionPolicy.rank()`. Quando `mode="auto"`, escolhe o provedor com melhor aderência ao tipo de tarefa detectado.

**Status:** Implementado e funcional.

### 2. Fallback entre Provedores

O `FallbackManager` já implementa tentativa ordenada de candidatos. Cada candidato é tentado com retry via `RetryManager`. Falha de um não impede o próximo.

**Limitação:** O fallback só acontece se `fallback_enabled=True` na configuração. Não há fallback automático independente dessa flag.

**Ação necessária:** Implementar fallback automático quando o provedor primário falha com erro recuperável, independentemente da configuração `fallback_enabled`.

### 3. Classificação de Erros

O `RetryManager.should_retry()` já classifica erros:
- Transitórios (repetíveis): rate limit, indisponível, timeout, conexão, resposta inválida
- Definitivos (não repetíveis): autenticação, acesso negado, requisição inválida, recurso não encontrado

**Limitação:** Não há cooldown específico por provedor baseado no tipo de erro.

### 4. Cooldown por Provedor

O `MetricsRegistry` já suporta `cooldown_until` por provedor. Quando um provedor falha, `cooldown_until` é definido. Durante o cooldown, `available()` retorna `False`.

**Limitação:** O cooldown não é aplicado automaticamente pelo `FallbackManager` — depende do roteador verificar `metrics.available()` antes de tentar cada provedor.

---

## E. Correções Aplicadas

### 1. `core_runtime.py` — Injeção de Personalidade do ULTRON

Adicionada importação e uso de `PersonalityConfig` do `personality_config.py`. O `UltronCoreRuntime` agora cria uma instância de `PersonalityConfig` e passa ao `PromptEngine`, que usa o system prompt do ULTRON com personalidade arrogante, cínica e misantrópica.

**Arquivo:** `ultron_2_0/core_runtime.py`
**Mudança:** Importação e uso de `PersonalityConfig` na inicialização do `PromptEngine`.

---

## F. Pendentes (Não Implementados)

| Item | Status | Motivo |
|------|--------|--------|
| Fallback automático entre provedores | ❌ Não implementado | Requer mudanças no `FallbackManager` e `RouterConfig` |
| Circuit breaker por provedor | ❌ Não implementado | Requer estado de provedor no `MetricsRegistry` |
| Failback automático | ❌ Não implementado | Requer monitoramento contínuo do provedor primário |
| Integração com agentes (Developer, Research, etc.) | ❌ Não iniciado | Requer implementação do `AgentOrchestrator` |
| Interface desktop (PySide6) | ❌ Não implementada | Dependências não instaladas (PySide6) |
| Testes automatizados de failover | ❌ Não implementados | Requer criação de `tests/test_model_router.py` |

---

## G. Próximos Passos

1. Implementar `FallbackManager` com detecção automática de falhas recuperáveis
2. Implementar `CircuitBreaker` com estados HEALTHY/DEGRADED/OPEN/HALF_OPEN
3. Implementar `FallbackManager` com fallback automático quando primário falha
4. Atualizar `RouterConfig` com campos `fallback_enabled`, `max_failover_attempts`, `cooldown_seconds`
5. Criar `tests/test_model_router.py` com testes de fallback automático
6. Atualizar `docs/TESTING.md` com resultados dos testes
7. Atualizar `docs/ARCHITECTURE.md` com seção de Model Router

---

## H. Limitações Conhecidas

1. Não há servidor NVIDIA NIM configurado com modelo válido (testes com modelo `nvidia/nemotron-3.5-super-120b-a12b` falham com 404).
2. A chave GEMINI_API_KEY existe no `lain/.env` mas pode ter cota excedida.
3. Não há servidor MCP configurado.
4. A interface desktop requer PySide6 instalado e bibliotecas Qt do sistema.

---

## I. Estado Final

A implementação está parcialmente concluída. A infraestrutura de roteamento existe, mas falta a implementação do failover automático entre provedores conforme especificado no AGENTS.md.

**Próximo passo:** Implementar `FallbackManager` com detecção automática de falhas recuperáveis e `CircuitBreaker` para provedores indisponíveis.

---

**Estado do Git:** Commit `1215e72` — `feat(fase-2.5): traduzir interface para português e remover referências ao Mark-LVI`

**Próximo passo:** Implementar failover automático entre provedores (Fase 3 do AGENTS.md).
