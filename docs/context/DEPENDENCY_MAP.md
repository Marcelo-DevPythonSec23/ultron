# DEPENDENCY_MAP — dependências e regras

## 1. Dependências externas (fixadas)

| Pacote | Versão | Uso | Onde |
|---|---|---|---|
| `fastapi` | >=0.115 | HUD e base do lain | `web/`, `lain/app/api` |
| `sqlalchemy` / `aiosqlite` | >=2.0 / >=0.20 | persistência assíncrona | `core_runtime` |
| `pydantic` / `pydantic-settings` | >=2.0 | modelos e settings | lain |
| `python-dotenv` | >=1.0 | `.env` do lain | `bootstrap` |
| `google-genai` | >=3.0,<4 | Gemini texto, STT Live, TTS | providers/voz |
| `psutil` | >=5.9 | `system_status` | Mark-LVI action |
| `ddgs` | >=9,<10 | `web_search` | Mark-LVI action |
| `uvicorn` | >=0.30 | servidor do HUD | `web/server` |
| `pytest` / `pytest-asyncio` | dev | testes | `tests/` |

Dependências do sistema (opcionais): `parec`/`arecord`, `aplay`/`paplay`,
`spd-say` (Linux).

**Conflito conhecido:** `Mark-LVI-main` declara `google-genai <3`; o 2.0 usa
`3.x`. Por isso o runtime Mark-LVI **não é executado** — apenas actions e
`memory_manager` são importados, e não dependem do SDK.

## 2. Grafo de importação (interno)

```text
cli ───────────────► orchestrator_bridge ──► core_runtime
voice/runner ──────► orchestrator_bridge        │
voice/pipeline ────► orchestrator_bridge        ├─► bootstrap
web/server ────────► orchestrator_bridge        ├─► tool_gateway ─► tool_contracts
web/app ───────────► (bridge injetado)          ├─► tool_loop
                                                ├─► marklvi_actions
                                                └─► memory_tools ─► bootstrap
voice/pipeline ────► voice/contracts
voice/stt_gemini ──► voice/contracts
voice/tts ─────────► voice/audio_io ─► voice/contracts
```

## 3. Regras de dependência (aplicadas)

1. `core_runtime` não importa `cli`, `web` nem `voice`.
2. `web` e `voice` importam `orchestrator_bridge`, nunca o contrário.
3. `tool_gateway` não importa providers.
4. `memory_tools` não importa `web`/`voice`.
5. `bootstrap` não importa módulos de alto nível.
6. Nenhum módulo do 2.0 altera `lain`/`Mark-LVI` em disco.

## 4. Dependências com os originais

| Módulo do 2.0 | Importa de | Tipo |
|---|---|---|
| `core_runtime` | `app.core.*`, `app.intelligence.*`, `app.database.*`, `app.models.*` | reutilização direta |
| `bootstrap` | `app.config.Settings` | reutilização |
| `tool_loop` | `app.intelligence.providers.base.LLMProvider`, `app.models.message.*` | contrato |
| `marklvi_actions` | `actions.system_monitor/open_app/web_search/reminder` | adaptação |
| `memory_tools` | `memory.memory_manager` | adaptação |

## 5. Ordem de inicialização

```text
bootstrap.ensure_sys_paths
  → Settings (.env absoluto, banco isolado)
  → engine + create_all
  → session
  → gateway (actions + memory)
  → ProviderRegistry (mock, gemini + ToolCallingProvider)
  → ChatService/ContextManager/PromptEngine → Orchestrator
```

Encerramento na ordem inversa: sessão → engine → orquestrador.

## 6. Variáveis de ambiente

| Variável | Efeito |
|---|---|
| `ULTRON2_PROJECT_ROOT` | raiz que contém `lain/` e `Mark-LVI-main/` |
| `DATABASE_URL` | sobrescrita pelo runtime para o banco do 2.0 |
| `GEMINI_API_KEY` | lida de `lain/.env`; nunca logada |
| `MAX_CONTEXT_TOKENS`, `MAX_HISTORY_MESSAGES`, `GEMINI_DEFAULT_MODEL` | settings do lain |

Ver `docs/SECURITY.md` para o tratamento de segredos.
