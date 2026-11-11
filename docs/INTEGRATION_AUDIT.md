# INTEGRATION_AUDIT — Auditoria Técnica ULTRON 2.0

**Status:** Fase 0 concluída. Documento aguardando aprovação para início da implementação.
**Data:** 2026-11-10
**Escopo:** Auditoria integral de `lain/` (ULTRON Core) e `Mark-LVI-main/` (Mark-LVI Runtime), incluindo a camada de integração pré-existente em `ultron-2.0/`.
**Método:** Leitura direta de código-fonte + evidência executável. Nenhuma afirmativa deste documento foi obtida por presunção; todo dado técnico foi verificado no código ou executado em ambiente isolado (banco de teste em `/tmp/opencode/ultron-audit/`, desde então removido; `lain/ultron.db` original intacto).

---

## Sumário executivo

1. **Os dois projetos são complementares, não redundantes** — ULTRON é núcleo conversacional/texto (FastAPI + orquestrador + providers + SQLite); Mark-LVI é runtime operacional de voz/desktop (Qt + áudio + 21 actions). A integração arquitetural é viável e desejável.
2. **O maior obstáculo técnico é a ausência de tool calling no núcleo ULTRON**: `LLMRequest` (`lain/app/models/message.py:35`) não possui campo `tools`, e `Orchestrator.process_chat` (`lain/app/core/orchestrator.py:31`) não executa nenhum ciclo de decisão de ferramentas. Integrar as actions do Mark-LVI exige estender o orquestrador do ULTRON — não o contrário.
3. **`core/stt.py` e `core/tts.py` do Mark-LVI são código morto**: nenhum módulo do projeto os importa. O áudio real vem do Gemini Live (loop principal em `main.py`) ou do stack opcional `providers/`. Integrá-los como se fossem o pipeline de voz seria implementar uma ficção.
4. **A camada pré-existente `ultron-2.0/` foi auditada e reprovada como integração real**: `orchestrator_bridge.process_text()` retorna a própria mensagem do usuário rotulada como `source: ultron-core` (`ultron-2.0/ultron_2_0/orchestrator_bridge.py:49-53`) — nunca invoca o orquestrador. Precisa ser reescrita, não expandida.
5. **Conflito de dependência**: venv do lain tem `google-genai 3.0.0`; Mark-LVI exige `>=2.8.0,<3`. PyQt6, faster-whisper, vosk, edge-tts, kokoro, miniaudio, pyautogui e playwright **não estão instalados** nesta máquina.
6. **Riscos de segurança concretos nas actions**: `game_updater` desativa o FAILSAFE do pyautogui (linha 353) e tem auto-shutdown; `computer_settings` usa `shell=True` (linhas 228/257); 11 de 21 actions leem `config/api_keys.json` diretamente.

---

## 1. Arquitetura atual do ULTRON (`lain/`)

### 1.1 Estrutura real

```text
lain/
├── app/
│   ├── main.py                  # FastAPI, lifespan, rotas
│   ├── config.py                # Settings (pydantic-settings, .env relativo ao CWD)
│   ├── api/                     # Rotas HTTP (conversas, mensagens, providers, health)
│   ├── core/
│   │   ├── orchestrator.py      # Ciclo conversacional completo (process_chat)
│   │   ├── chat_service.py      # Persistência de mensagens/conversas
│   │   └── context_manager.py   # Janela de contexto, truncamento por tokens
│   ├── database/                # SQLAlchemy + aiosqlite, modelos e repositórios
│   ├── intelligence/
│   │   ├── providers/           # registry.py, base.py, gemini.py, mock.py
│   │   └── prompt_engine.py     # Montagem de LLMRequest + system prompt
│   └── models/                  # ChatRequest/ChatResponse, LLMRequest, MessageRole
├── tests/                       # 64 testes (todos passando — verificado)
├── ultron.db                    # SQLite: 12 conversas, 48 mensagens (INTOCADO)
├── .env                         # GEMINI_API_KEY real (NUNCA imprimir o valor)
└── .venv/                       # Único ambiente Python funcional do projeto
```

### 1.2 O ciclo conversacional (`Orchestrator.process_chat`, `lain/app/core/orchestrator.py:31-116`)

Fluxo real, em 9 passos encadeados:

1. Resolve provedor/modelo (`request.provider` ou default do registry).
2. Obtém/cria conversa (`chat_service.get_or_create_conversation`).
3. Persiste a mensagem do usuário.
4. Recupera histórico recente (`get_recent_chat_messages`, limit = `context_manager.max_messages`).
5. Filtra/trunca por janela de tokens (`context_manager.build_context`).
6. Monta o `LLMRequest` via `prompt_engine.assemble_request`.
7. Despacha ao provedor — streaming (`generate_response_streaming` + `on_chunk`) ou bloqueante (`generate_response`).
8. Persiste a resposta do assistente (com usage e metadata).
9. Retorna `ChatResponse` estruturada.

**Observações críticas:**
- **Não há tool calling.** `LLMRequest` (`lain/app/models/message.py:35`) carrega apenas mensagens/instrução/modelo/temperatura; busca por `tools` em todo `lain/app/intelligence` não retorna nenhum resultado. O orquestrador é 100% texto→LLM→texto.
- **Streaming existe a nível provider** (`on_chunk` callback), mas não é exposto via HTTP como SSE.
- **Assíncrono de ponta a ponta** (FastAPI/asyncio/aiosqlite).
- **System prompt** define a persona vilanesca ULTRON em pt-BR (via `prompt_engine`).
- **`env_file=".env"` é relativo ao CWD** (`lain/app/config.py:51`) — o health_check do Gemini só funciona executando a partir de `lain/`. Isso será um ponto de atenção na integração (o runtime unificado não poderá assumir CWD=`lain/`).

### 1.3 Providers (`lain/app/intelligence/providers/`)

- `ProviderRegistry` (`registry.py:13-46`): catálogo `dict[str, LLMProvider]`, registro em `create_default_registry` (mock sempre + Gemini via `cfg.get_gemini_api_key()`), singleton global `get_provider_registry()`.
- `GeminiProvider` usa SDK `google-genai` (versão instalada: **3.0.0**).
- `MockProvider` disponível sempre — útil para testes sem rede.
- Contrato base em `base.py` (`LLMProvider.generate_response`, `generate_response_streaming`, `health_check`).

### 1.4 Estado git e dados

- `lain/` é repositório git (branch `main`), com **1 alteração não-commitada preexistente** em `.env.example` — preservada, não descartada.
- `lain/ultron.db`: 12 conversas, 48 mensagens — intacto durante toda a auditoria.

---

## 2. Arquitetura atual do Mark-LVI (`Mark-LVI-main/`)

### 2.1 Estrutura real

```text
Mark-LVI-main/
├── main.py              # Loop de voz real (Gemini Live) em thread asyncio; ui.py na thread Qt
├── ui.py                # ÚNICO QApplication; HUD (JarvisUI) com métodos thread-safe
├── core/
│   ├── action_loader.py    # Contrato TOOL/ActionRegistry das actions
│   ├── gemini.py           # Acesso a modelos com deadlines + fallback ladder
│   ├── confirm.py          # Gate de confirmação 90s (token emitido pela interface, não pelo modelo)
│   ├── outcome.py          # Protocolo status done/unverified/failed/ask/started + untrusted()
│   ├── undo.py             # Pilha de reversão (push_undo)
│   ├── wake_word.py        # openwakeword, modelo "hey_jarvis" (linha 28)
│   ├── audio_devices.py    # Seleção de dispositivos
│   ├── stt.py              # MORTO — ver 2.3
│   └── tts.py              # MORTO — ver 2.3
├── actions/             # 21 arquivos; 17 tool modules com TOOL + 4 helpers sem TOOL
├── plugins/            # Plugins descobertos por existência de arquivo
├── providers/           # Stack opcional de STT/TTS/LLM ("pipeline mode") + schema.py
├── memory/              # config_manager.py (api_keys.json), memory_manager.py (fatos em JSON)
└── dashboard/           # Frontend local de acompanhamento
```

### 2.2 O loop de voz real (`main.py`)

- Sessão de voz Gemini Live mantida em event loop asyncio **em thread de background**; a janela vive na **thread principal Qt** (`ui.py`, único `QApplication`).
- Captura: `sd.InputStream` 16kHz int16, blocksize 1024 (sounddevice).
- Tools rodam em **worker threads**, nunca na thread Qt (regra central do `Mark-LVI-main/AGENTS.md`).
- O áudio primário do produto é o **Gemini Live** (bidirecional). O stack `providers/` é um caminho alternativo ("pipeline mode": STT local → LLM → TTS local).

### 2.3 Achado central: `core/stt.py` e `core/tts.py` são código morto

Busca de imports em todo o projeto: **nenhum módulo importa `core.stt` ou `core.tts`** (única referência a TTS em `providers/_tests.py` é a `tts_piper`, módulo diferente do stack `providers/`). O AGENTS.md master lista esses arquivos como pontos de partida, mas a evidência mostra que o pipeline de voz real **não passa por eles**. Consequências:

- Integrar `core/stt.py`/`core/tts.py` como "o STT/TTS do Mark-LVI" seria integrar uma ilusão.
- A camada pré-existente `ultron-2.0/ultron_2_0/voice_runtime.py` importa essas classes mortas e reporta `available: True` enganosamente (imports lazy mascaram a desconexão) — um dos motivos da reprovação dela (ver seção 2.5).
- Para voz no ULTRON 2.0, as opções reais são: (a) Gemini Live como no `main.py`, ou (b) stack `providers/` (faster-whisper/vosk + edge-tts/kokoro/...), ou (c) ambos com seleção — todas exigindo as dependências hoje ausentes.

### 2.4 Contrato real das actions (`core/action_loader.py`)

- Cada tool module exporta `TOOL = {"name": ..., "description": ..., "parameters": {...}}` (linha 11).
- `ActionRegistry.run(name, parameters, ctx)` (linha 157) injeta contexto com `_CTX_KEYS = ("player", "speak", "response", "session_memory")` (linha 39).
- Assinatura de handler: `def handler(parameters, response=None, player=None, session_memory=None) -> str` — com **5 variantes legais**, resolvidas por introspecção.
- 17 módulos com `TOOL` + 4 helpers sem `TOOL` (`proactive`, `background_monitor`, `screen_processor`, `system_monitor`).
- Retorno é sempre `str` (o assistente transforma em fala). `get_system_status()` (`actions/system_monitor.py:113`) retorna `dict` internamente.
- Actions novas seguem o protocolo `core/outcome.py` (`status=done/unverified/failed/ask/started`).

### 2.5 A camada pré-existente `ultron-2.0/` — auditada e reprovada

Resultado da auditoria do trabalho anterior (3/3 testes passam, mas os testes validam o comportamento errado):

| Problema | Evidência |
|---|---|
| **Eco, não integração**: `process_text()` devolve a mensagem do usuário rotulada `source: ultron-core` sem nunca invocar `Orchestrator.process_chat` | `ultron_2_0/orchestrator_bridge.py:42-53` |
| **Importa código morto**: `voice_runtime` importa `core.stt`/`core.tts` (mortos) e reporta `available: True` | `ultron_2_0/voice_runtime.py` |
| **Segundo mecanismo de decisão**: `_fallback_command` decide por regex fora do orquestrador | `ultron_2_0/tool_registry.py` |
| **Funciona por engano**: `tool_registry` de fato executa 3 tools com assinaturas reais (`open_app`, `system_status`, `web_search`) — a única parte aproveitável como referência | `ultron_2_0/tool_registry.py` |

**Veredicto:** a camada atual simula integração. Deve ser reescrita (aproveitando o que foi validado), não expandida. Este documento é o registro formal dessa reprovação.

---

## 3. Responsabilidade de cada componente relevante

### ULTRON (`lain/`) — autoridade intelectual

| Componente | Responsabilidade | Veredito para 2.0 |
|---|---|---|
| `app/core/orchestrator.py` | Ciclo conversacional completo | **Preservar** + estender para tool calling |
| `app/intelligence/providers/registry.py` | Catálogo de LLMs | **Preservar como autoridade única de LLM** |
| `app/intelligence/prompt_engine.py` | System prompt + montagem de request | **Preservar** + estender para injetar contratos de tools |
| `app/core/chat_service.py` + `app/database/` | Persistência de conversas | **Preservar** (único histórico) |
| `app/core/context_manager.py` | Janela de contexto | **Preservar** |
| `app/api/` | Interface HTTP | **Preservar** |
| `app/config.py` | Settings | **Adaptar** (resolver dependência de CWD `.env`) |

### Mark-LVI (`Mark-LVI-main/`) — infraestrutura operacional

| Componente | Responsabilidade | Veredito para 2.0 |
|---|---|---|
| `main.py` | Loop de voz Gemini Live + threads | **Adaptar** (extrair o ciclo de voz, descartar a orquestração própria de sessão) |
| `ui.py` | HUD Qt (thread-safe) | **Adaptar** (re-tematizar para identidade ULTRON) |
| `core/action_loader.py` | Registro/execução de actions | **Reutilizar** como base dos tool adapters |
| `core/confirm.py` | Gate de confirmação 90s | **Reutilizar** (design exemplar: token emitido pela interface, não pelo modelo) |
| `core/outcome.py` | Protocolo de status + `untrusted()` anti-injection | **Reutilizar** |
| `core/undo.py` | Pilha de reversão | **Reutilizar** |
| `core/wake_word.py` | openwakeword "hey_jarvis" | **Opcional** (dependência ausente) |
| `core/audio_devices.py` | Seleção de dispositivos | **Reutilizar** |
| `core/gemini.py` | Acesso a modelos com fallback ladder | **Não integrar como autoridade** — substituir pelo registry do ULTRON |
| `core/stt.py`, `core/tts.py` | — | **Não integrar** (código morto) |
| `providers/schema.py` | Conversão de tool declarations Gemini/OpenAI/Anthropic + budget | **Reutilizar** (crítico: o ULTRON precisará declarar tools em multi-formato) |
| `memory/memory_manager.py` | Fatos persistentes em JSON | **Adaptar** (decidir política de persistência sob autoridade do ULTRON) |
| `memory/config_manager.py` | `config/api_keys.json` | **Adaptar** (nunca escrever o arquivo diretamente; nenhum existe hoje) |
| `actions/` (21) | Ferramentas de desktop/browser/sistema | **Adaptar** via adapters com contrato explícito |
| `dashboard/` | Frontend local | **Opcional** (avaliar vs. UI Qt) |

---

## 4. Dependências internas e externas

### ULTRON (`lain/requirements.txt` + venv verificado)

fastapi, uvicorn, sqlalchemy, aiosqlite, pydantic, pydantic-settings, google-genai (==3.0.0 instalado), httpx, pytest (dev). **Instalados e funcionais** — 64/64 testes passam no venv.

### Mark-LVI (`requirements.txt`)

**Presentes na máquina:** sounddevice, numpy, psutil (via venv lain ou sistema).
**Ausentes (verificado por import):** PyQt6, faster-whisper, vosk, edge-tts, kokoro, miniaudio, pyautogui, playwright, openwakeword, soundfile.
**Resultado do teste de importação das 21 actions no venv lain: 20/21 OK; `browser_control` falha com `ImportError: browser_control needs playwright, which is not installed`.**

### Execução de validação realizada (não-destrutiva)

- lain: **64/64 testes** passando (SQLite em memória via `tests/conftest.py`).
- ultron-2.0 pré-existente: 3/3 passando (mas validam o comportamento-eco — ver 2.5).
- Inicialização do núcleo ULTRON validada com banco isolado em `/tmp` (settings, providers, tabelas criadas).
- Execução real de tool: `system_status` retornou métricas reais via `get_system_status()` (CPU/memória do host).
- Hardware: 3,7 GiB RAM, 4 CPUs, sem GPU; áudio Intel HDA + PulseAudio **funcionando** (12 devices) — voz é viável, mas modelos locais grandes não.

---

## 5. Bibliotecas compartilhadas

| Biblioteca | ULTRON | Mark-LVI | Compatibilidade |
|---|---|---|---|
| Python | 3.12.3 (venv lain) | requer 3.11–3.13 | ✅ compatível |
| google-genai | **3.0.0** (instalado) | `>=2.8.0,<3` | ❌ **conflito** (ver seção 6) |
| psutil | sim | sim | ✅ |
| numpy / sounddevice | — | sim | ✅ (instaláveis) |
| SQLite (lain) vs JSON (Mark-LVI memory) | — | — | padrões distintos, sem conflito de biblioteca |

---

## 6. Dependências incompatíveis

1. **`google-genai` 3.0.0 vs `>=2.8.0,<3`** — o venv funcional do lain já está na versão maior. O Mark-LVI nunca foi executado nesta máquina (não há `config/api_keys.json`), então sua exigência de pin não foi validada em produção aqui. **Decisão de arquitetura necessária**: padronizar em 3.0.0 e adaptar o que depender de APIs <3, OU criar ambiente separado. Recomendação preliminar: único runtime com google-genai 3.0.0, validando se as chamadas do Mark-LVI que usam o SDK são compatíveis (a maior parte do Mark-LVI usa REST/Gemini Live, não o SDK — verificação a fazer na implementação).
2. **PyQt6 e stack de áudio ausentes** — qualquer integração de voz/UI exige instalação nova no venv (ou venv dedicado). Não há conflito de versão conhecido, apenas ausência.
3. **CWD-sensitividade do lain** (`app/config.py:51`, `env_file=".env"`): o runtime unificado não pode assumir CWD=`lain/` sem quebrar o carregamento da chave. Exige adapter de ambiente no terceiro repositório.

---

## 7. Conflitos de inicialização

1. **Dois ciclos de vida**: FastAPI/uvicorn (lain) vs. QApplication + event loop em background thread (Mark-LVI). Solução proposta: um processo único onde o Qt é opcional (modo desktop) e a API é opcional (modo server), ambos controlados pelo bootstrap do ULTRON 2.0 — nunca dois orquestradores.
2. **CWD**: carregar `.env` do lain por caminho absoluto resolvido, não por CWD.
3. **Event loops**: o loop asyncio do lain (API) e o loop de sessão de voz do Mark-LVI precisam de um único gerenciador de loops no runtime unificado, com a thread Qt mantida apenas para UI.

## 8. Conflitos de estado

- Mark-LVI mantém `session_memory` (ctx de tools) + sessão de voz ativa; ULTRON mantém conversas/mensagens em SQLite. **Regra proposta:** `session_memory` = estado transitório de execução de tools (não persistente, por chamada); SQLite do ULTRON = único histórico durável da mesma conversa. Nenhum componente do Mark-LVI escreve no banco do ULTRON diretamente.
- `config/api_keys.json` (Mark-LVI) vs `.env`/Settings (lain): **duas fontes de credencial**. Decisão de arquitetura: o ULTRON 2.0 usa as Settings do lain como fonte primária; o `config_manager` do Mark-LVI é adaptado para ler de lá (ou mantido apenas para settings operacionais não-secretas), sem duplicar a GEMINI_API_KEY.

## 9. Conflitos de memória

- `memory/memory_manager.py` do Mark-LVI persiste **fatos** (JSON, chave/valor/categoria — `remember()` linha 404, recall via `recall_memory` tool), não transcripts. É complementar ao histórico conversacional do ULTRON, não duplicado. **Proposta:** integrar como tool (`remember`/`recall`) sob autoridade do ULTRON, com política explícita do que merece persistência (nada de dump automático de outputs de tools).
- Contexto: `ContextManager` do lain permanece o único construtor de contexto de LLM.

## 10. Conflitos de provedores de IA

- **Dois acessos a Gemini por caminhos distintos**: ULTRON via SDK `google-genai` no `ProviderRegistry`; Mark-LVI via `core/gemini.py` (fallback ladder) + Gemini Live (REST/WebSocket) no loop de voz. **Decisão:** o ProviderRegistry do ULTRON permanece a autoridade para **geração de texto**; o Gemini Live é tratado como **serviço de voz** (camada de interface), não como segundo registry. `core/gemini.py` não é integrado como autoridade; ferramentas que hoje o chamam passam a receber o texto do modelo via o caminho do orquestrador ULTRON, ou continuam com `core.gemini` apenas como dependência interna de tools que precisam de sub-processamento — a decidir na implementação, com teste.
- **Credencial única**: uma GEMINI_API_KEY (a do `.env` do lain), nunca duplicada em `api_keys.json`.

## 11. Compatibilidade dos sistemas de áudio

- Hardware: compatível (PulseAudio OK, 12 devices). Sem GPU — Whisper local só em configuração pequena (`faster-whisper` tiny/base) se o modo pipeline local for escolhido.
- **Fluxo real do Mark-LVI**: Gemini Live (bidirecional, baixa dependência local) é o caminho primário e o mais adequado ao hardware; o stack `providers/` é o fallback local opcional.
- `core/wake_word.py` (openwakeword) e `core/audio_devices.py` são reutilizáveis; wake word é opcional e sob demanda (RAM limitada).
- Conclusão: **compatível**, com a ressalva central de que stt.py/tts.py são mortos e não são o pipeline.

## 12. Compatibilidade dos sistemas de ferramentas

- O contrato Mark-LVI (`TOOL` + `ActionRegistry.run`) é sólido e homogêneo, mas **assíncrono-incompatível por design**: actions são síncronas (worker threads), o orquestrador do lain é asyncio. O adapter de execução precisará de ponte thread↔loop (`asyncio.to_thread`/run_in_executor).
- Incompatibilidade de **decisão**: o núcleo ULTRON não tem tool calling — o `LLMRequest`/`prompt_engine`/`base.py` precisam de extensão (campo tools + loop de execução). Isso é evolução do núcleo do ULTRON, justificada tecnicamente e exigida pelo objetivo (não é o Mark-LVI ditando o núcleo; é o núcleo ganhando a capacidade que lhe falta).
- `providers/schema.py` do Mark-LVI (conversões to_openai/to_anthropic/to_gemini + budget de declarações) é diretamente reaproveitável nessa extensão.

## 13. Componentes reutilizáveis (verificados)

| Componente | Evidência de funcionalidade |
|---|---|
| `core/action_loader.py` (contrato + registry de actions) | 20/21 actions importam OK; `ActionRegistry.run` executa com introspecção de assinatura |
| `core/confirm.py` (gate 90s) | Leitura integral: token emitido pela interface, `resolve()` roda em worker thread, expira em `TIMEOUT_SECONDS=90` (linha 46) |
| `core/outcome.py` (`untrusted()` linha 188 + protocolo de status) | Protocolo aplicado nas actions novas |
| `core/undo.py` (`push_undo` linha 60) | Usado por actions reversíveis |
| `core/audio_devices.py` | Seleção de dispositivos |
| `core/wake_word.py` | openwakeword `hey_jarvis` (linha 28) — dependência ausente, mas design válido |
| `providers/schema.py` | Conversões completas de tool declarations (linhas 156/175/190) + `budget` (linha 272) |
| `memory/memory_manager.py` | Fatos JSON com `remember`/recall (linhas 404/351) |
| Actions (ver Etapa 2 do plano): `open_app`, `system_monitor` (`get_system_status` linha 113), `web_search`, `reminder`, `weather_report`, `youtube_video`, `flight_finder`, `send_message`, `video_player`, `file_controller` (com gates), `desktop`, `computer_control` (com gates) | Importam OK no venv lain; execução real validada apenas para `system_status` |

## 14. Componentes que precisam de adaptação

| Componente | Adaptação necessária |
|---|---|
| Núcleo ULTRON (`orchestrator.py`, `prompt_engine.py`, `models/message.py`, `providers/base.py`) | Adicionar campo `tools` ao `LLMRequest`, loop de tool calling no orquestrador, interpretação de resultados via protocolo `outcome` — **no terceiro repositório, estendendo sem alterar `lain/`** |
| `main.py` do Mark-LVI | Extrair o ciclo de voz (Gemini Live) como módulo de runtime de voz; descartar a orquestração de sessão própria |
| `ui.py` | Re-tematizar para identidade ULTRON (vermelho/preto/grafite); manter a thread Qt como camada de interface |
| `app/config.py` do lain | Resolver `.env` por caminho absoluto no runtime unificado |
| `memory/config_manager.py` | Fonte de credencial unificada (nunca escrever `api_keys.json` diretamente) |
| Actions com risco | Gates/limites via camada de segurança (ver secção 16) |
| `ultron-2.0/` pré-existente | Reescrita: substituir eco por chamada real a `Orchestrator.process_chat`; remover imports de código morto; eliminar `_fallback_command` |

## 15. Componentes que não devem ser integrados

| Componente | Motivo |
|---|---|
| `core/stt.py`, `core/tts.py` | Código morto — nada os importa; a "integração" deles seria ficção |
| `core/gemini.py` como autoridade de LLM | Segunda autoridade de decisão; o registry do ULTRON prevalece (AGENTS.md seção 8) |
| Loop de sessão/conversa do `main.py` | Segundo orquestrador; proibido (AGENTS.md 3.2) |
| Histórico/transcripts próprios do Mark-LVI | Dois históricos para a mesma conversa; proibido (AGENTS.md 3.2) |
| `_fallback_command` (regex) do `ultron-2.0/` | Segundo mecanismo de decisão; proibido (AGENTS.md 3.2) |
| `game_updater` (integração inicial) | Desativa FAILSAFE do pyautogui (linha 353) + auto-shutdown sem gate (linha 633+); só integrar com redline de segurança explícito e aprovação separada |
| Execução irrestrita de shell (`computer_settings` `shell=True` linhas 228/257) | Envolver em allowlist/whitelist + confirmação; nunca expor direto ao modelo |
| `dev_agent`/`code_helper`/`file_processor` (fase inicial) | Executam código; exigem sandbox/limites antes de expor ao loop do modelo |

---

## 16. Riscos técnicos identificados

### Riscos de segurança (ações concretas verificadas)

| # | Risco | Evidência | Severidade |
|---|---|---|---|
| S1 | FAILSAFE do pyautogui desativado | `actions/game_updater.py:353` | Alta |
| S2 | Shutdown do sistema sem gate de confirmação | `actions/game_updater.py:633` (`_system_shutdown`), agendado em 1005-1031 | Alta |
| S3 | `shell=True` com input montável | `actions/computer_settings.py:228,257` | Alta |
| S4 | Execução de código por action | `dev_agent`, `code_helper`, `file_processor` | Alta |
| S5 | Perfis reais do navegador expostos | `browser_control` (playwright obrigatório; `ImportError` se ausente) | Média |
| S6 | 11/21 actions leem `config/api_keys.json` diretamente | ex. `web_search.py:73`, `dev_agent.py:19`, `computer_settings.py:43` (lista completa na auditoria) | Média |
| S7 | Prompt injection via resultado de tool | Mitigação existente: `core/outcome.py:188` (`untrusted()`) — precisa ser aplicada no novo loop | Média |

### Riscos técnicos

| # | Risco | Mitigação proposta |
|---|---|---|
| T1 | Estender o núcleo ULTRON (tool calling) sem quebrá-lo | Terceiro repositório estende via composição; testes lain 64/64 como regressão contínua |
| T2 | Conflito `google-genai` 3.0.0 vs <3 | Padronizar 3.0.0; auditar usos de SDK no Mark-LVI; Gemini Live usa REST — verificar |
| T3 | Ponte threads↔asyncio nas actions | Adapter com `asyncio.to_thread` + timeouts |
| T4 | RAM 3,7 GiB sem GPU | Gemini Live como voz primária; modelos locais só under-demand (tiny/base) |
| T5 | Dependência de CWD do lain | Bootstrap resolve caminhos absolutos |
| T6 | Qt + asyncio + FastAPI no mesmo processo | Um gerenciador de ciclo de vida único; Qt opcional; modos de operação |
| T7 | Reescrita do `ultron-2.0/` pré-existente pode perder o que funciona | Aproveitar `tool_registry` (3 tools validadas) como referência de contrato real |
| T8 | Fuga de credenciais em logs | Nunca logar `GEMINI_API_KEY`; auditoria de logging na implementação |

---

## Plano de integração por etapas (proposto — aguarda aprovação)

Cada etapa é pequena, testável e reversível; após cada uma: rodar testes, verificar imports/logs/dependências, documentar. **Nenhuma etapa toca `lain/` ou `Mark-LVI-main/`** — todo trabalho ocorre em estrutura independente (reforma do `ultron-2.0/` existente + inicialização de git com ponto de restauração).

**Etapa 0 — Fundação (repositório terceiro)**
- Reformular `ultron-2.0/`: git init (raiz não é repo), branch de trabalho, commit de restauração.
- Resolver bootstrap de caminhos (`.env` do lain por caminho absoluto; CWD-independente).
- Substituir o eco: `process_text` chama `Orchestrator.process_chat` de verdade (via ponte assíncrona), com teste B (conversação texto ponta a ponta com MockProvider — sem gastar quota).

**Etapa 1 — Tool calling no núcleo (extensão, não modificação do lain)**
- Wrapper do orquestrador no terceiro repo que estende o ciclo: campo `tools` no request montado pelo adapter, loop de decisão do modelo → validação de contrato → execução → interpretação (protocolo `outcome`).
- Reutilizar `providers/schema.py` para declarações multi-formato.
- Teste E: descoberta/validação/execução de tools com `system_status` (não-destrutivo, já validado).

**Etapa 2 — Tool adapters (subset seguro)**
- Adapter por tool com contrato explícito (nome/descrição/parâmetros/tipos/obrigatórios/resultado/exceções/permissões/confirmação/timeout/estratégia de erro — AGENTS.md 7.1).
- Primeiro subset: `system_status`, `web_search`, `open_app`, `reminder` (leitura/consulta, sem destrutividade).
- Integração de `core/confirm.py`, `core/outcome.py`, `core/undo.py` na camada de segurança.
- Gates para `computer_settings`/`file_controller`/`computer_control` apenas depois da camada de confirmação ativa.

**Etapa 3 — Voz (entrada/saída)**
- Adapter de voz com dois modos: Gemini Live (extraído do `main.py`) e pipeline local opcional (stack `providers/`), instalação de dependências primeiro.
- Wake word opcional (`core/wake_word.py`), sob demanda.
- STT → `process_chat` (mesmo fluxo do texto — sem segunda conversa). Resposta textual sempre disponível; TTS falha → texto permanece.
- Testes C/D/F.

**Etapa 4 — Memória**
- `memory_manager` (fatos) como tools `remember`/`recall` sob autoridade do ULTRON; política de persistência explícita (nada automático).

**Etapa 5 — UI/identidade**
- HUD Qt re-tematizado (vermelho escuro/luminoso, preto, grafite, transparências, indicadores de voz/processamento/tools/providers) com tokens de cor centralizados; estados reais, sem botões fictícios.

**Etapa 6 — Validação final**
- Testes A–G do AGENTS.md; regressão lain 64/64; critérios de aceitação 1–15.

### Itens explicitamente pendentes de decisão do usuário

1. **Padrão `google-genai` 3.0.0** (recomendado) vs. downgrade/ambiente separado.
2. **Modo de voz primário**: Gemini Live (recomendado para este hardware) vs. pipeline local vs. ambos.
3. **Subset inicial de actions** (proposta acima) — incluir/excluir módulos.
4. **`game_updater`, `dev_agent`, `code_helper`, `file_processor`**: integrar com redlines, adiar, ou descartar.
5. **Venv**: estender o venv do lain (único funcional) vs. criar venv novo dedicado ao ULTRON 2.0 (recomendado novo, copiando pins).
6. **UI Qt vs. dashboard web** do Mark-LVI como base visual.

---

## Conclusão

A integração é arquiteturalmente viável e o desenho de autoridade do AGENTS.md é confirmado pela auditoria: **ULTRON como núcleo inteligente (estendido com tool calling), Mark-LVI como fonte de componentes operacionais (actions, áudio real do Gemini Live/providers, mecanismos de segurança).** Os três bloqueadores a resolver são: (1) ausência de tool calling no núcleo, (2) camada pré-existente `ultron-2.0/` que simula integração (eco), (3) dependências de áudio/Qt ausentes + conflito de pin do google-genai. Nenhum deles é estrutural — são todos solucionáveis com os adaptadores planejados.

**Este documento encerra a Fase 0. A implementação não começou. Aguardo aprovação.**
