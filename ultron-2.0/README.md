# ULTRON 2.0

ULTRON 2.0 é a integração, em uma terceira estrutura independente, do núcleo
inteligente **ULTRON** (`lain/`) com a infraestrutura operacional **Mark-LVI**
(`Mark-LVI-main/`):

- **ULTRON** permanece a única autoridade de conversa: orquestrador, contexto,
  prompt, provedores, histórico e memória.
- **Mark-LVI** fornece componentes operacionais reutilizados: actions
  (ferramentas) e a base de áudio/STT do Gemini Live.
- Nenhum dos dois repositórios originais é modificado, copiado ou sobrescrito.
  O 2.0 os importa via `sys.path` e isola seus próprios dados.

> Escopo real: o que está implementado e validado está descrito abaixo. Recursos
> ainda não integrados (wake word, VAD, confirmação interativa, ações de
> escrita/execução) aparecem em **Limitações**, não como concluídos.

## Requisitos

- Linux (testado com PulseAudio/PipeWire e ALSA)
- Python **3.12**
- `uv` para criar o venv (ou `python -m venv`)
- Opcional para voz: `parec`/`arecord` (captura) e `aplay`/`paplay` (reprodução)
- Opcional: `GEMINI_API_KEY` no `lain/.env` (texto via Gemini, STT e TTS)

Nenhuma GPU é necessária; não há modelo local pesado.

## Instalação

```bash
cd ultron-2.0

# venv dedicado (decisão nº 5 da auditoria)
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python pytest pytest-asyncio
```

O `.env` do núcleo é lido de `../lain/.env` por caminho absoluto. A chave nunca
é impressa, copiada ou gravada em outro lugar.

## Uso

Todos os comandos partem de `ultron-2.0/`.

### Texto (CLI)

```bash
./.venv/bin/python -m ultron_2_0                 # REPL
./.venv/bin/python -m ultron_2_0 --demo          # estado + ferramentas e sai
./.venv/bin/python -m ultron_2_0 --message "olá" # um turno e sai
```

Comandos do REPL (não vão ao modelo): `/status`, `/tools`, `/new`, `/quit`.
Opções: `--provider mock|gemini`, `--database <url>`, `--no-tools`, `--verbose`.

### Voz

```bash
./.venv/bin/python -m ultron_2_0.voice --list-devices
./.venv/bin/python -m ultron_2_0.voice                 # microfone → STT → núcleo → TTS
./.venv/bin/python -m ultron_2_0.voice --no-tts        # resposta só em texto
./.venv/bin/python -m ultron_2_0.voice --audio fala.wav --no-tts
./.venv/bin/python -m ultron_2_0 --voice               # atalho pela CLI principal
```

A voz é **interface**: o texto reconhecido entra no mesmo
`OrchestratorBridge.process_text` da CLI. Detalhes em `docs/VOICE_PIPELINE.md`.

### HUD web

```bash
./.venv/bin/python -m ultron_2_0.web                   # http://127.0.0.1:8765
./.venv/bin/python -m ultron_2_0.web --port 8765 --open
```

O HUD mostra estado real (providers, ferramentas, banco, memória, áudio),
conversa persistida e execução de ferramentas. Não há botões fictícios. O bind
padrão é local; não exponha em rede sem revisar `docs/SECURITY.md`.

## O que funciona hoje

| Recurso | Estado |
|---|---|
| Conversa por texto pelo orquestrador original do lain | ✅ implementado e testado |
| Histórico único e persistente em `data/ultron2.db` | ✅ |
| Tool calling (protocolo JSON) com 7 ferramentas | ✅ |
| `system_status` (métricas reais), `open_app`, `web_search`, `reminder` | ✅ adaptadas do Mark-LVI |
| `remember` / `recall` / `forget` (memória explícita em `data/memory.json`) | ✅ (`forget` recusado sem confirmação) |
| STT via Gemini Live (somente transcrição) | ✅ implementado; requer chave |
| TTS via Gemini ou voz do sistema | ✅ implementado; falha preserva o texto |
| Pipeline de voz reusando o mesmo núcleo | ✅ testado |
| HUD web local com estado real e chat | ✅ |
| Recuperação de falhas (provedor, dispositivo, conexão, tool, TTS) | ✅ 10 testes |
| Wake word / VAD / barge-in | ❌ não integrados |
| Confirmação interativa de ações destrutivas | ❌ não implementada (gate recusa) |
| Actions de escrita/execução (`file_controller`, `dev_agent`, etc.) | ❌ desconectadas por segurança |

## Dados e isolamento

| Item | Local |
|---|---|
| Banco do 2.0 | `ultron-2.0/data/ultron2.db` |
| Memória de fatos do 2.0 | `ultron-2.0/data/memory.json` |
| Banco original do usuário | `lain/ultron.db` — **nunca tocado** |
| Memória original do Mark-LVI | `Mark-LVI-main/memory/long_term.json` — **nunca tocado** |
| Credenciais | `lain/.env` (somente leitura) |

`Mark-LVI-main/config/api_keys.json` não existe e não deve ser criado.

## Estrutura

```text
ultron-2.0/
├── ultron_2_0/
│   ├── bootstrap.py          # caminhos absolutos + Settings + banco isolado
│   ├── core_runtime.py       # wiring do núcleo lain e loop dedicado
│   ├── orchestrator_bridge.py# ponta de entrada única (texto/voz/HUD)
│   ├── tool_contracts.py     # ToolContract/ToolResult
│   ├── tool_gateway.py       # allowlist, validação, timeout, auditoria
│   ├── tool_loop.py          # ToolCallingProvider (protocolo JSON)
│   ├── marklvi_actions.py    # subset curado de actions
│   ├── memory_tools.py       # remember/recall/forget
│   ├── cli.py                # interface de texto
│   ├── voice/                # STT, TTS, áudio, pipeline
│   └── web/                  # HUD FastAPI/uvicorn
├── data/                     # dados do 2.0 (criados em execução)
├── tests/                    # 88 testes
├── scripts/run_demo.py
├── pyproject.toml / requirements.txt
└── README.md
```

## Testes

```bash
./.venv/bin/python -m pytest -q          # 88 passed
cd ../lain && ./.venv/bin/python -m pytest -q   # 64 passed (regressão)
```

Detalhes, mapa A–G do AGENTS.md e limitações em `docs/TESTING.md`.

## Documentação

- `docs/INTEGRATION_AUDIT.md` — auditoria, riscos e decisões aprovadas
- `docs/ARCHITECTURE.md` — arquitetura implementada e responsabilidades
- `docs/INTEGRATION_MAP.md` — módulos originais e destinos
- `docs/VOICE_PIPELINE.md` — captura, STT, núcleo, TTS e reprodução
- `docs/TOOLS.md` — contratos e execução das ferramentas
- `docs/SECURITY.md` — permissões, validação, auditoria e pendências
- `docs/TESTING.md` — testes, resultados e limitações
