# MODEL_ROUTER — Model Router do ULTRON 2.1 (Fase 3)

> **Status:** IMPLEMENTADO (Fase 3 concluída). Ver `docs/context/TECHNICAL_DECISIONS.md`
> (ADR-014), `tests/test_routing.py` (41 testes) e `docs/roadmap/ULTRON_21_PHASE3_REPORT.md`.

## 1. Objetivo

Permitir que o ULTRON selecione e coordene diferentes provedores de modelo de IA,
escolhendo o modelo conforme o tipo de tarefa, com fallback, timeout e retry com
backoff — sem criar um segundo orquestrador conversacional nem expor credenciais.

O `ModelRouter` é uma **camada de seleção e encaminhamento**, não um segundo
orquestrador. Ele envolve o `ProviderRegistry` do lain (autoridade de registro
preservada) e é passado ao `Orchestrator` no lugar do registry (duck typing do
contrato: `default_provider_id`, `get_provider`, `list_providers`,
`register_provider`).

## 2. Arquitetura do pacote `routing/`

```
ultron_2_0/routing/
├── __init__.py       # API pública (incl. AUTO_MODEL = "auto")
├── router.py         # ModelRouter, RouterConfig, RoutingProvider
├── capabilities.py   # TaskType, ModelCapabilities, infer_task_type
├── catalog.py        # ModelCatalog, build_catalog (overrides explícitos por tarefa)
├── policy.py         # ModelSelectionPolicy, Candidate (ranking determinístico)
├── retry.py          # RetryPolicy, RetryManager (backoff, classificação de erros)
├── fallback.py       # FallbackManager (tentativa ordenada de candidatos)
├── metrics.py        # MetricsRegistry, sanitize_error (sem credenciais)
└── adapters.py       # ProviderAdapter (timeout, stream até 1º chunk)
```

## 3. Fluxo de um turno

```text
Orchestrator (lain)
  → registry.default_provider_id + get_provider(...)
     → ModelRouter.get_provider() → RoutingProvider
        → ModelRouter.dispatch(request) / iter_stream(request)
           → infer_task_type(última mensagem do usuário)   (dados, sem modelo)
           → ModelSelectionPolicy.rank()                   (catálogo + política)
           → ProviderAdapter (cópia da requisição + modelo fixado)
              → asyncio.wait_for (timeout) → provedor real
           → FallbackManager + RetryManager (ordem de candidatos, backoff, cooldown)
              → último erro propagado sem embrulho (contrato do lain preservado)
```

### Decisões de projeto (ADR-014)

1. **Provedor padrão = primário.** A política ordena os demais apenas como
   fallback. `mode="primary"` (default) preserva o comportamento atual.

2. **Fallback entre provedores é opt-in** (`ULTRON_ROUTER_FALLBACK`, default `0`).
   Trocar silenciosamente de provedor muda custo/qualidade/privacidade; a
   decisão fica explícita na configuração operacional.

3. **`mock` nunca é fallback automático** (`allow_mock_fallback`). É provedor
   de teste/offline.

4. **Provedor/modelo escolhidos explicitamente são respeitados** e desligam o
   fallback daquele turno.

5. **`mode="auto"`** (opt-in via `ULTRON_ROUTER_MODE=auto`): a política escolhe
   o provedor por tipo de tarefa a cada turno; `RoutingProvider.default_model`
   retorna o sentinela `"auto"`; o modelo real é escolhido por tarefa e gravado
   na mensagem do assistente (o `ChatService` do lain grava o provedor/modelo
   da **resposta**, não os da conversa).

6. **Retry classifica erros:**
   - Transitórios (repetíveis): rate limit, indisponível, timeout, conexão,
     resposta inválida → retry com backoff exponencial limitado.
   - Definitivos (não repetíveis): autenticação, acesso negado, requisição
     inválida, recurso não encontrado.
   - Exceções desconhecidas são tratadas como transitórias (uma tentativa extra).

7. **Última exceção propagada sem embrulho** — o contrato de erro do lain e os
   testes existentes continuam válidos.

8. **Overrides de modelo por tarefa** (`model_overrides`) são decisões
   explícitas do catálogo, não dependem de empate de score.

9. **Métricas e snapshots nunca expõem credenciais** — `sanitize_error` remove
   padrões de chave/token/segredo e limita o tamanho.

## 4. Configuração (`RouterConfig`)

Lida de variáveis de ambiente `ULTRON_ROUTER_*` (sem tocar em credenciais):

| Variável | Padrão | Significado |
|---|---|---|
| `ULTRON_ROUTER_ENABLED` | `1` | ativa/desativa o roteador |
| `ULTRON_ROUTER_MODE` | `primary` | `primary` (padrão primário) ou `auto` (política por tarefa) |
| `ULTRON_ROUTER_FALLBACK` | `0` | fallback entre provedores (opt-in) |
| `ULTRON_ROUTER_TIMEOUT` | `45.0` | timeout por chamada (segundos) |
| `ULTRON_ROUTER_MAX_ATTEMPTS` | `2` | tentativas por candidato |
| `ULTRON_ROUTER_BACKOFF` | `0.25` | backoff base (segundos) |
| `ULTRON_ROUTER_MAX_BACKOFF` | `4.0` | backoff máximo (segundos) |
| `ULTRON_ROUTER_COOLDOWN` | `30.0` | cooldown após falha (segundos) |
| `ULTRON_ROUTER_ALLOW_MOCK_FALLBACK` | `0` | permite `mock` como fallback |
| `ULTRON_ROUTER_PROVIDERS` | `` (vazio) | allowlist de provedores (vazio = todos) |
| `ULTRON_ROUTER_MODELS` | `` | JSON: `{provedor: {tarefa: modelo}}` overrides explícitos |

Exemplo de overrides por tarefa:

```json
{"gemini": {"code": "gemini-3.5-pro", "reasoning": "gemini-3.5-pro"}, "mock": {"cheap": "mock-lite"}}
```

## 5. Tipos de tarefa (`TaskType`)

Inferência determinística da última mensagem do usuário (sem chamada de modelo):

| Tipo | Critério |
|---|---|
| `long_context` | ≥ 4.000 chars ou frase de "texto abaixo/documento/log" |
| `code` | palavras: código, programar, função, classe, refatorar, bug, python, sql, api, etc. |
| `reasoning` | palavras: analisar, comparar, explicar, por que, arquitetura, estratégia, avaliar, etc. |
| `cheap` | palavras: resumir, traduzir, listar, formatar, classificar, converter, extrair |
| `chat` | padrão (qualquer outra coisa) |

Um `task` explícito sempre vence a heurística.

## 6. Segurança

- `lain/` e `Mark-LVI-main/` **nunca modificados**.
- `GEMINI_API_KEY` nunca entra em prompts, logs ou snapshots.
- `sanitize_error` remove padrões `AIza...`, `sk-...`, `*KEY=...` etc.
- `to_public_dict()` expõe apenas dados de configuração (nenhum segredo).
- Falhas de provedor são isoladas: cooldown por provedor, não derruba o núcleo.
- `ProviderTimeoutError` do contrato do lain para estouro de timeout.

## 7. Integração no núcleo

`ultron_2_0/core_runtime.py`:

- Cria `ModelRouter(self.registry, config=router_config)`.
- Passa `provider_registry=self.router` ao `Orchestrator` (duck typing).
- `register_provider` delega ao router (que atualiza o catálogo e reseta métricas).
- `shutdown` limpa `self.router`.

`ultron_2_0/orchestrator_bridge.py`:

- Aceita `router_config` no construtor.
- `status()["router"]` expõe snapshot completo do roteador.

`ultron_2_0/cli.py`:

- `/status` exibe estado do roteador, fallback, timeout, tentativas e falhas recentes.

## 8. Testes

`tests/test_routing.py` — 41 testes com provedores reais do contrato `LLMProvider`
(`StubProvider` com identidade própria, falhas, delay, streaming; sem rede):

1. Inferência determinística de tipo de tarefa (chat/code/reasoning/long_context/cheap).
2. Catálogo/capacidades e ranking da política (ordenação, exclusão, bôndo ao preferido).
3. Retry com backoff exponencial limitado e classificação de erros (transitório vs definitivo).
4. Métricas, cooldown e sanitização de segredos (`AIza`, `sk-`).
5. Seleção/fallback/timeout entre dois provedores distintos.
6. Isolamento de falhas, provedor/modelo explícitos, `mock` nunca como fallback.
7. Streaming com failover apenas antes do primeiro chunk (não depois de saída parcial).
8. Configuração por env sem credenciais; tolera valores inválidos.
9. Modo `auto`: `default_model` retorna `"auto"` sem provedor explícito; seleção por tipo de tarefa; respeito a provedor/modelo explícitos.
10. Integração real pelo `OrchestratorBridge` (histórico único, provedor real persistido).

Resultados registrados: **177 passed** (ULTRON 2.0), **64 passed** (regressão lain),
`secret_leak: False` no smoke de status.

## 9. Limitações conhecidas

- Busca semântica/embeddings não fazem parte do roteador (Fase 6).
- Cooldown e pendências de autorização vivem em memória (reiniciar descarta).
- Não há agendador automático de `expire()`/`consolidate()` (operações de API).
- Provedores reais (Gemini) exigem rede e `GEMINI_API_KEY`; testes usam stubs locais.
- `mode="auto"` é opt-in; o padrão continua sendo `primary` para não trocar
  custo/privacidade silenciosamente.

## 10. Próximas etapas

- Fase 4: Sistema Multiagente (`AgentOrchestrator`, `AgentRegistry`, etc.).
- Fase 5: Integração com agentes CLI (OpenCode, Claude Code) e servidores MCP.
- Fase 6: Busca semântica opcional (embeddings) sem virar dependência obrigatória.
- Criptografia em repouso e backup/restauração de `data/`.
