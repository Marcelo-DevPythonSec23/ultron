# PROJECT_CONTEXT — ULTRON 2.0

> Porta de entrada de contexto para qualquer agente. Leia este arquivo antes de
> trabalhar. O mapa documental completo está em
> [`docs/context/CONTEXT_INDEX.md`](docs/context/CONTEXT_INDEX.md).
> Este documento descreve o projeto **real**, não uma arquitetura idealizada.

## 1. Identidade

- **Nome:** ULTRON 2.0.
- **Objetivo:** unificar o núcleo inteligente ULTRON (`lain/`) com a
  infraestrutura operacional Mark-LVI (`Mark-LVI-main/`) em um único assistente,
  sem dois orquestradores concorrentes.
- **Problema que resolve:** o ULTRON original conversa, mas não executa ações
  nem fala com áudio próprio; o Mark-LVI executa e fala, mas possui um segundo
  ciclo cognitivo. O 2.0 mantém **um cérebro** e reaproveita **um corpo**.
- **Visão de longo prazo:** assistente pessoal local, modular e extensível, com
  texto, voz e HUD sobre um único histórico/memória, capaz de trocar provedores
  de IA e adicionar ferramentas sem reescrever o núcleo.
- **Princípios:**
  1. ULTRON é a única autoridade de conversa, contexto, memória e decisão.
  2. Mark-LVI fornece capacidades operacionais por interfaces explícitas.
  3. Segurança no código, nunca apenas no prompt.
  4. Nada é declarado pronto sem teste/evidência.
  5. `lain/` e `Mark-LVI-main/` permanecem intactos.

## 2. Origem e relação entre os diretórios

| Diretório | Papel | Estado no 2.0 |
|---|---|---|
| `lain/` | ULTRON Core: orquestrador, contexto, prompt, providers, SQLite, API FastAPI | **Preservado e reutilizado** por importação (`sys.path`); **nunca modificado** |
| `Mark-LVI-main/` | Runtime operacional: ações de desktop, áudio, memória JSON, HUD original | **Fonte de componentes**: actions e `memory_manager` reaproveitados; o loop de voz original **não** é executado |
| `ultron-2.0/` | Produto final da integração | **Onde todo o código novo vive** |

O 2.0 **não copia** os projetos: importa módulos e isola seus dados
(`data/ultron2.db`, `data/memory.json`). O banco real `lain/ultron.db` e o
`Mark-LVI-main/memory/long_term.json` nunca são tocados.

## 3. Arquitetura (fato de código)

```text
Interface: CLI de texto · voz · HUD web
        │
        ▼
OrchestratorBridge (ultron_2_0/orchestrator_bridge.py)
        │  mantém apenas o conversation_id da sessão de interface
        ▼
Orchestrator do lain (app/core/orchestrator.py)   ← único ciclo conversacional
        ├── ChatService + SQLite do 2.0 (histórico único)
        ├── ContextManager + PromptEngine (janela e personalidade)
        └── ProviderRegistry (autoridade de provedores)
                └── MemoryInjectionProvider (memória por turno)  ← extensão 2.0
                        └── ToolCallingProvider (tool_loop.py)   ← extensão 2.0
                                └── ToolGateway (tool_gateway.py)
                                        └── actions do Mark-LVI (subset curado)

MemoryEngine (memory_engine.py)  ← fornece DADOS ao núcleo, não decide
        ├── memory.json           (canônico: escopos global/user:default)
        ├── memory_records.json   (tipo, escopo, trust, versão, validade)
        └── memory_history.json   (versões + tombstone de exclusão)
```

Componentes reais (detalhes em `docs/context/MODULE_MAP.md`):

- **Núcleo:** `core_runtime.py` monta o núcleo por composição.
- **Providers:** `mock` e `gemini` (registrados no `ProviderRegistry` do lain).
- **Ferramentas (7):** `system_status`, `open_app`, `web_search`, `reminder`,
  `remember`, `recall`, `forget`.
- **Voz:** `voice/` — `SubprocessMicrophone`, `GeminiLiveSTT`,
  `GeminiBatchTranscriber`, `GeminiTTS`, `SystemSpeaker`, `VoicePipeline`.
- **HUD:** `web/` — FastAPI + HTML local, sem CDN.
- **Memória:** `memory_engine.py` sobre o `memory_manager` do Mark-LVI
  (`memory_tools.py` é a fachada); `memory_injection.py` injeta o bloco no turno.
  Tipos, escopo, versão, retenção e consolidação em `docs/memory/`.
- **Infra:** `bootstrap.py` — raízes absolutas, `.env` do lain, banco isolado.

## 4. Estado atual (com evidência)

| Área | Estado | Evidência |
|---|---|---|
| Conversa por texto no orquestrador do lain | `IMPLEMENTED` | `tests/test_bridge.py`, `test_core_runtime.py` |
| Histórico único persistente | `IMPLEMENTED` | `data/ultron2.db`, `test_bridge.py` |
| Tool calling + gateway | `IMPLEMENTED` | `test_tool_loop.py`, `test_tool_gateway.py` |
| 7 ferramentas do subset curado | `IMPLEMENTED` | `gateway.names()`, `test_integration_tools.py` |
| Memória explícita `remember/recall/forget` | `IMPLEMENTED` | `test_memory_tools.py` (8), `test_memory_engine.py` (17) |
| Memória tipada/versionada/consolidação | `IMPLEMENTED` | `memory_engine.py`, `test_memory_engine.py`, `docs/memory/` |
| Injeção de memória no prompt (por turno) | `IMPLEMENTED` | `memory_injection.py`, `test_memory_engine.py` |
| Busca semântica (embeddings) | `PLANNED` | não há provedor nem dependência |
| STT Gemini Live (só transcrição) | `IMPLEMENTED` (requer chave/rede/microfone) | `test_voice_pipeline.py`, `test_voice_units.py` |
| TTS Gemini / voz do sistema | `IMPLEMENTED` (validado ao vivo) | `docs/TESTING.md` |
| Voz reusando o mesmo núcleo | `IMPLEMENTED` | `test_voice_pipeline.py`, `test_faults.py` |
| HUD web local | `IMPLEMENTED` | `test_web.py` (11) |
| Recuperação de falhas | `IMPLEMENTED` | `test_faults.py` (10) |
| Wake word / VAD / barge-in | `PLANNED` (não existe) | — |
| Confirmação interativa de ações destrutivas | `PLANNED` (gate recusa) | `test_memory_tools.py` |
| Actions de escrita/execução | `BLOCKED` por segurança | `docs/INTEGRATION_MAP.md` |
| Model Router | `PLANNED` (não implementar fictício) | — |
| MCP / agentes externos | `PLANNED` | — |

## 5. Restrições

- **Hardware:** Linux, ~4 GB RAM, sem GPU. Nada de modelo local pesado.
- **Python:** 3.12; venv dedicado `ultron-2.0/.venv`; `google-genai 3.0.0`.
- **Rede/credenciais:** texto/TTS/STT Gemini exigem `GEMINI_API_KEY` em
  `lain/.env` (somente leitura). A chave nunca é impressa.
- **Áudio:** `parec`/`arecord` e `aplay`/`paplay` opcionais; ausência vira erro
  controlado, nunca queda do núcleo.
- **Segurança:** allowlist de ferramentas, validação de parâmetros, timeout,
  confirmação para ações sensíveis, resultados externos tratados como dados não
  confiáveis.
- **Compatibilidade:** `Mark-LVI-main` exige `google-genai <3`; por isso o 2.0
  **não executa** o runtime Mark-LVI, apenas importa actions isoladas.
- **Não modificar:** `lain/`, `Mark-LVI-main/`, `lain/ultron.db`,
  `Mark-LVI-main/config/api_keys.json`.

## 6. Como verificar o estado real

```bash
cd ultron-2.0
./.venv/bin/python -m pytest -q                    # 109 testes do 2.0
cd ../lain && ./.venv/bin/python -m pytest -q      # 64 testes de regressão
./.venv/bin/python -m ultron_2_0 --demo            # estado + ferramentas
```

- Contexto e decisões: `docs/context/`.
- Memória: `docs/memory/`.
- Integração: `docs/INTEGRATION_AUDIT.md`.
- Uso: `ultron-2.0/README.md`.

## 7. Regras de ouro para agentes

1. Leia este arquivo + `CONTEXT_INDEX.md` + `AGENTS.md`.
2. Carregue só o contexto especializado da tarefa.
3. Verifique o código antes de acreditar na documentação.
4. Não crie segundo orquestrador, segunda memória ou histórico paralelo.
5. Não invente API: leia a assinatura real.
6. Não declare pronto sem teste/evidência.
7. Registre decisões em `docs/context/TECHNICAL_DECISIONS.md`.
8. Preserve `lain/` e `Mark-LVI-main/` intactos.
