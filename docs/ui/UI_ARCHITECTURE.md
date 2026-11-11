# UI_ARCHITECTURE — arquitetura de apresentação do HUD

**Fase:** 2.5
**Data:** 2026-11-11
**Princípio central:** a interface é uma **camada de apresentação e interação**;
o ULTRON continua sendo a única autoridade de conversa, histórico e memória.

## 1. Separação de responsabilidades

```text
Navegador (HTML/CSS/JS)
  │  fetch JSON
  ▼
FastAPI (ultron_2_0/web/app.py)      ← apresentação: rotas, validação, erros HTTP
  │  chamadas Python
  ▼
OrchestratorBridge                   ← estado da sessão de interface
  │
  ▼
UltronCoreRuntime                    ← wiring do núcleo
  ├── Orchestrator do lain           ← único ciclo conversacional
  ├── ToolCallingProvider / Gateway  ← ferramentas + autorização
  ├── MemoryEngine                   ← memória canônica
  └── ProviderRegistry               ← provedores
```

- O navegador **não** importa módulos do núcleo nem acessa banco/memória.
- O `app.py` não contém lógica de conversa: só encaminha e serializa estado.
- Não há histórico paralelo: o painel de conversa lê `/api/history`, que vem do
  `ChatService` do lain.

## 2. Camadas do front-end

| Camada | Onde | Responsabilidade |
|---|---|---|
| Identidade | bloco `:root` de `static/index.html` | tokens de cor, tipografia, raio, movimento |
| Estrutura | HTML semântico | header, 3 colunas, painéis, gavetas, formulário |
| Estado | objeto `state` no JS | `ready`, `busy`, `error`, `metrics`, `providers`, `tools`, `motion`, `compact` |
| Comunicação | função `api()` | `fetch` + tratamento de erro JSON/HTTP |
| Renderização | funções `load*`/`set*` | uma função por fonte de dados |
| Animação | `drawCore()`/`animate()` | canvas abstrato por estado real |
| Acessibilidade | atributos ARIA + CSS | foco visível, `aria-live`, skip link, movimento reduzido |

Cada `load*` tem um único endpoint e um único dono de dado; não há estado
duplicado entre JS e backend.

## 3. Contratos HTTP

| Método | Rota | Dado real | Falha |
|---|---|---|---|
| GET | `/` | HTML local, sem CDN | — |
| GET | `/api/status` | `bridge.status()` + áudio + `busy` | áudio vira `{error}`; nunca derruba |
| GET | `/api/system` | `system_snapshot()` (psutil/Mark-LVI) | `503` com motivo; sem números inventados |
| GET | `/api/activity` | `ActivityLog` da sessão | lista vazia |
| GET | `/api/tools` | contratos do `ToolGateway` | lista vazia se sem gateway |
| GET | `/api/history` | mensagens persistidas pelo núcleo | erro controlado |
| GET | `/api/approvals` | `bridge.pending_actions()` (sem token) | erro controlado |
| POST | `/api/chat` | um turno por `bridge.process_text` | `502` com tipo/mensagem |
| POST | `/api/new` | encerra conversa (histórico preservado) | — |
| POST | `/api/approvals/{id}/approve` | libera token de uso único | `404`/`409` |
| POST | `/api/approvals/{id}/reject` | recusa e invalida | `404`/`409` |

## 4. Fluxo de um turno

```text
composer submit
  → POST /api/chat {message, provider}
  → app.py: inflight += 1; ActivityLog.record("turn")
  → asyncio.to_thread(bridge.process_text)      (não bloqueia o event loop)
  → Orchestrator (lain) → provider → [tools] → resposta
  → histórico persistido no SQLite do 2.0
  → app.py: ActivityLog.record(tool/reply)
  → JSON com content/provider/model/usage/tool_calls/elapsed_seconds
  → front: loadHistory + loadStatus + loadActivity
```

O `inflight` é o único estado de "ocupado" (`status.busy`); não há barra de
progresso falsa.

## 5. Autorização (Fase 2) na interface

```text
tool sensível → AuthorizationManager.request() → pending_action
  → GET /api/approvals (poll 1 s) → painel com ferramenta + argumentos exatos
  → usuário decide → POST .../approve | .../reject
  → token de uso único consumido → ToolGateway executa ou recusa
```

O modelo nunca vê o token nem chama esses endpoints. A voz sempre recusa
(`_deny_sensitive_action`). Tokens expirados/reutilizados/argumentos alterados
são rejeitados pelo `AuthorizationManager`.

## 6. Tratamento de erros

- Erro de rede/HTTP → `#banner` com `role="alert"` + estado do núcleo em erro.
- `/api/system` indisponível → medidores mostram "indisponível"; nenhum número
  é inventado.
- Falha de turno → `502`; o HUD recarrega o histórico e continua operacional.
- Falha de áudio → `status.audio.error`; não impede texto.

## 7. Responsividade

| Faixa | Layout |
|---|---|
| > 1200 px | 3 colunas: sistema · conversa · atividade/ferramentas |
| 781–1200 px | 2 colunas; painéis da direita em grade 2× |
| ≤ 780 px | 1 coluna empilhada; relógio/metadados ocultos; header quebra |

## 8. Movimento e acessibilidade

- `prefers-reduced-motion` desliga CSS e animação do canvas; o estado continua
  legível por texto (`aria-live`).
- Controle "Reduzir movimento" e "Layout compacto" mudam o estado real do HUD.
- Skip link, foco visível, navegação por teclado, `role="log"`,
  `role="progressbar"` com `aria-valuenow`, gavetas com `aria-expanded`.
- Canvas marcado `aria-hidden="true"`; o estado é sempre textual.

## 9. Restrições respeitadas

- Nenhum arquivo de `lain/` ou `Mark-LVI-main/` foi modificado.
- Nenhuma credencial é copiada, exibida ou registrada.
- O HUD escuta em `127.0.0.1` por padrão; não abre microfone.
- Voz permanece em processo separado (`python -m ultron_2_0.voice`).
