# INTEGRATION_MAP — módulos originais e destinos

Mapa do que foi **reutilizado, adaptado, mantido fora ou descartado** na
construção do ULTRON 2.0. Nenhum arquivo de `lain/` ou `Mark-LVI-main/` foi
modificado, copiado ou apagado; tudo abaixo é importação via `sys.path` ou
reimplementação controlada em `ultron-2.0/`.

## 1. ULTRON (`lain/`) — preservado como núcleo

| Módulo original | Papel | Uso no ULTRON 2.0 |
|---|---|---|
| `app/core/orchestrator.py` | Ciclo único de conversa | **Reutilizado sem alteração** — instanciado pelo runtime |
| `app/core/chat_service.py` | Persistência de conversa | **Reutilizado** |
| `app/core/context_manager.py` | Contexto/truncamento | **Reutilizado** |
| `app/intelligence/prompt_engine.py` | Montagem do prompt | **Reutilizado** |
| `app/intelligence/providers/registry.py` | Autoridade de provedores | **Reutilizado** (mock + gemini) |
| `app/intelligence/providers/base.py` | Contrato `LLMProvider` | **Reutilizado** — é o contrato do `ToolCallingProvider` |
| `app/models/message.py` | `LLMRequest`/`LLMResponse`/`ChatMessage` | **Reutilizado** (tools entram por prompt, sem alterar o modelo) |
| `app/database/*` | Modelos e repositórios | **Reutilizado** com banco isolado |
| `app/config.py` | `Settings`/`.env` | **Reutilizado**, com `.env` absoluto e `DATABASE_URL` sobrescrito |
| `app/main.py`, `app/api/*` | API FastAPI do lain | **Não executados** — o 2.0 tem seu próprio HUD |
| `lain/ultron.db` | Banco real do usuário | **Nunca tocado** (12 conversas/48 mensagens preservadas) |

## 2. Mark-LVI — reutilizado por adaptação

### 2.1 Actions conectadas (subset curado, decisão nº 3)

| Original | Tool no 2.0 | Timeout | Observação |
|---|---|---|---|
| `actions/system_monitor.py::get_system_status` | `system_status` | 10 s | helper sem `TOOL`; wrapper manual devolve JSON de métricas |
| `actions/open_app.py` | `open_app` | 20 s | via `ActionRegistry.run`, `ctx={}` |
| `actions/web_search.py` | `web_search` | 30 s | requer rede; sem grounding cai no fallback DDG (`ddgs`) |
| `actions/reminder.py` | `reminder` | 15 s | grava em `~/.jarvis/reminders` (efeito real no sistema) |

As declarações (nome/descrição/parâmetros) vêm do próprio loader do Mark-LVI;
o gateway mantém contrato, permissões, timeout e auditoria.

### 2.2 Infraestrutura reutilizada

| Original | Uso no 2.0 |
|---|---|
| `core/action_loader.py` | descoberta de actions e `ActionRegistry.run` (caminho público) |
| `providers/schema.py::to_prompt` | renderização das declarações no system prompt |
| `core/outcome.py` | princípio: resultado vira **fato** para o modelo escrever a frase |
| `memory/memory_manager.py` | `remember`/`search_memory`/`forget`; `MEMORY_PATH` redirecionado para `ultron-2.0/data/memory.json` |
| `main.py` (api Gemini Live) | **apenas a parte de áudio** foi reimplementada em `voice/stt_gemini.py` (Live com `response_modalities=["TEXT"]` + transcrição de entrada) |

### 2.3 Deliberadamente não integrado

| Original | Motivo |
|---|---|
| `main.py` (loop de sessão/conversa) | segundo orquestrador — proibido |
| histórico/transcripts próprios | dois históricos para a mesma conversa |
| `providers/*` como autoridade de LLM | segunda autoridade de decisão |
| `core/stt.py`, `core/tts.py` | código morto (nada os importa); a "integração" seria fictícia |
| `core/wake_word.py`, VAD | dependências ausentes no ambiente; recurso não validado |
| `dashboard/`, `ui.py` (Qt) | decisão nº 6: HUD web local substitui a UI pesada |
| `config/api_keys.json` | não existe e **não deve ser criado/editado** |

### 2.4 Actions descobertas e mantidas desconectadas

Descoberta completa roda (mesmo scan do boot do Mark-LVI), mas só o subset
curado recebe contrato. Motivos por action:

| Action | Motivo |
|---|---|
| `game_updater` | desativa `pyautogui.FAILSAFE` e agenda shutdown sem gate (S1/S2) |
| `computer_settings` | `shell=True` com entrada montável (S3) |
| `dev_agent`, `code_helper`, `file_processor` | executam código (S4) |
| `browser_control` | exige `playwright` ausente e expõe perfis reais (S5) |
| `file_controller`, `computer_control`, `desktop` | operações de escrita/controle; gates ainda não ligados à interface |
| demais (`weather_report`, `youtube_video`, `flight_finder`, `send_message`, `video_player`, …) | fora do subset aprovado; integração futura exige revisão de segurança |

## 3. Camada 2.0 — o que foi reescrito/removido

| Item pré-existente | Destino |
|---|---|
| `ultron_2_0/voice_runner.py`, `voice_runtime.py`, `main.py`, `run_voice.py` | **removidos** — continham eco e decisão por regex (segundo mecanismo de decisão) |
| `tool_registry.py` (stub) | **substituído** por `tool_contracts.py` + `tool_gateway.py` reais |
| `orchestrator_bridge.py` (eco) | **reescrito** para chamar `Orchestrator.process_chat` |
| `data/` vazio | recebe `ultron2.db`/`memory.json` apenas em execução real |

## 4. Fluxo de arquivos na execução

```text
ultron-2.0/ultron_2_0/bootstrap.py
  ├── resolve raízes: <projeto>/lain, <projeto>/Mark-LVI-main
  ├── sys.path: lain/ e Mark-LVI-main/
  ├── Settings(_env_file=<lain>/.env, DATABASE_URL=ultron-2.0/data/ultron2.db)
  └── importa SOMENTE:
        app.core.*, app.intelligence.*, app.models.*, app.database.*   (lain)
        core.action_loader, providers.schema, memory.memory_manager     (Mark-LVI)
```

## 5. Invariantes verificadas

- `lain/` e `Mark-LVI-main/` sem alterações do 2.0 (ver `docs/TESTING.md`).
- `lain/ultron.db`: 12 conversas / 48 mensagens, inalterado.
- `Mark-LVI-main/memory/long_term.json`: nunca lido/escrito.
- `Mark-LVI-main/config/api_keys.json`: inexistente, não criado.
- Uma única conversa por sessão de interface, em todos os modos.
