# ULTRON 2.0

**ULTRON 2.1 — Pós-integração / Arquitetura Multiagente**  
Linguagem principal: Python 3.12 · Ambiente: Linux  
Produto: `ultron-2.0/` · Especificações e documentação: raiz do repositório

---

## O que é o ULTRON 2.0

O ULTRON 2.0 unifica o núcleo inteligente **ULTRON** (`lain/`) com a infraestrutura operacional **Mark-LVI** (`Mark-LVI-main/`) em um único assistente, sem dois orquestradores concorrentes.

- **ULTRON** permanece a única autoridade de conversa, contexto, prompt, provedores, histórico e memória.
- **Mark-LVI** fornece componentes operacionais reutilizados (actions de desktop, áudio, STT via Gemini Live, base de TTS).
- Nenhum dos dois repositórios originais é modificado, copiado ou sobrescrito. O 2.0 os importa via `sys.path` e isola seus próprios dados (`data/ultron2.db`, `data/memory.json`).

---

## Estado das fases (conforme `AGENTS.md` e `INTERFACE.md`)

| Fase | Nome | Estado | Evidência |
|------|------|--------|-----------|
| 0 | Reavaliação do projeto | ✅ Concluída | `docs/roadmap/ULTRON_21_ASSESSMENT.md` |
| 1 | Documentação e controle de versão | ✅ Concluída | repositório raiz, índice unificado, `TECHNICAL_DECISIONS.md` |
| 2 | Autorização interativa | ✅ Concluída | `ultron_2_0/authorization.py`, 14 testes |
| 2.5 | Interface (HUD web + desktop) | ✅ Concluída | HUD web: 21 testes; Interface desktop PySide6: 12 testes; `docs/ui/` |
| 3 | Model Router | ✅ Concluída | `ultron_2_0/routing/`, 41 testes |
| 4 | Multiagente | ✅ Concluída | `ultron_2_0/agents/`, 21 testes |
| 5 | CLI/MCP | ✅ Concluída | `ultron_2_0/integrations/`, 19 testes |
| 6 | Evolução da memória | ✅ Concluída | `memory_semantic.py`, `memory_backup.py`, `memory_encryption.py`, 16 testes |
| 7 | Autonomia operacional | ✅ Concluída | `ultron_2_0/autonomy/`, 21 testes |
| 8 | Validação e estabilização | ✅ Concluída | `docs/roadmap/ULTRON_21_FINAL_REPORT.md` |

---

## Interface (conforme `INTERFACE.md`)

O `INTERFACE.md` especifica a reconstrução da interface do Mark LVI dentro do ULTRON 2.0.

### O que está implementado (Fase 2.5 — HUD web)

- **HUD web local** em `ultron_2_0/web/` (FastAPI + uvicorn, bind `127.0.0.1:8765`, sem CDN).
- Tema ULTRON (preto profundo, vermelho escuro/luminoso, grafite, elementos holográficos).
- Chat persistente, histórico único, ferramentas, aprovações, métricas reais do host, atividade da sessão.
- Voz como interface (não abre microfone no HUD; roda em processo separado).
- 21 testes aprovados em `tests/test_web.py`.

Documentação da interface:
- `docs/ui/INTERFACE_AUDIT.md`
- `docs/ui/UI_ARCHITECTURE.md`
- `docs/ui/UI_COMPONENTS.md`
- `docs/ui/UI_FUNCTIONALITY_MATRIX.md`
- `docs/ui/UI_TESTING.md`

### Interface desktop (PySide6 — especificação no `INTERFACE.md`)

A interface desktop está **implementada e conectada ao backend** (mesmo `OrchestratorBridge` da CLI e HUD web — nenhum segundo cérebro, histórico paralelo ou mecanismo de decisão independente).

- `ultron_2_0/interface/` — pacote completo (14 arquivos, ~2.400 linhas)
  - `application.py` — Application Controller (ponto de entrada)
  - `adapters/bridge_adapter.py` — conexão ao OrchestratorBridge (status, chat, ferramentas, memória, agentes, integrações, autonomia)
  - `events/event_system.py` — EventSystem (eventos estruturados entre interface e backend)
  - `themes/ultron_theme.py` — tema preto/vermelho do ULTRON (tokens CSS/QSS)
  - `animations/holographic_canvas.py` — canvas holográfico com estados (IDLE, LISTENING, PROCESSING, SPEAKING, ERROR, etc.)
  - `components/avatar.py` — avatar central com estados visuais
  - `components/chat.py` — chat integrado ao núcleo
  - `panels/systems_panel.py` — painel de sistema com métricas reais (CPU, RAM, GPU, etc.)
  - `panels/tasks_panel.py` — painel de tarefas com estados reais (done, unverified, failed, started)
  - `windows/main_window.py` — janela principal (layout 3 colunas + gavetas)
- `tests/test_interface.py` — 12 testes aprovados (modo offscreen)

---

## Ponto de entrada único — `main.py`

```bash
cd ultron-2.0
./.venv/bin/python main.py              # menu interativo de escolha da interface
./.venv/bin/python main.py --cli        # CLI de texto (REPL)
./.venv/bin/python main.py --web        # HUD web (FastAPI/uvicorn)
./.venv/bin/python main.py --desktop    # interface desktop PySide6 (janela)
./.venv/bin/python main.py --demo       # estado + ferramentas e sai
```

O `main.py` inicia o software completo: conecta a interface escolhida ao mesmo
`OrchestratorBridge` do núcleo ULTRON, sem criar um segundo cérebro, histórico
paralelo ou mecanismo de decisão independente.

---

## Como executar

Todos os comandos partem de `ultron-2.0/`.

### Instalação

```bash
cd ultron-2.0
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python pytest pytest-asyncio
```

> O `.env` do núcleo é lido de `../lain/.env` por caminho absoluto. A chave `GEMINI_API_KEY` nunca é impressa, copiada ou gravada em outro lugar.

### Texto (CLI)

```bash
./.venv/bin/python -m ultron_2_0                 # REPL
./.venv/bin/python -m ultron_2_0 --demo          # estado + ferramentas e sai
./.venv/bin/python -m ultron_2_0 --message "olá" # um turno e sai
```

Comandos do REPL: `/status`, `/tools`, `/new`, `/quit`.

### Voz

```bash
./.venv/bin/python -m ultron_2_0.voice --list-devices
./.venv/bin/python -m ultron_2_0.voice           # microfone → STT → núcleo → TTS
./.venv/bin/python -m ultron_2_0.voice --no-tts  # resposta só em texto
```

A voz reusa o mesmo núcleo (`OrchestratorBridge.process_text`).

### HUD web

```bash
./.venv/bin/python -m ultron_2_0.web             # http://127.0.0.1:8765
```

O HUD mostra estado real (providers, ferramentas, banco, memória, áudio), conversa persistida e execução de ferramentas. Não há botões fictícios. O bind padrão é local; não exponha em rede sem revisar `docs/SECURITY.md`.

### Interface desktop (PySide6)

```bash
./.venv/bin/python -m ultron_2_0.interface       # janela com avatar holográfico
```

Interface desktop completa com avatar holográfico, chat integrado ao núcleo,
painéis de sistema e tarefas, controles de voz e diagnóstico. Requer
`PySide6` (adicionado aos requisitos). Funciona em modo offscreen para
desenvolvimento sem display gráfico.

---

## Testes

```bash
# Suíte do ULTRON 2.0
cd ultron-2.0
./.venv/bin/python -m pytest -q          # 264 passed, 1 skipped

# Regressão do núcleo original (inalterado)
cd ../lain
./.venv/bin/python -m pytest -q          # 64 passed
```

| Suíte | Resultado |
|-------|-----------|
| ULTRON 2.0 (incl. Fases 2.5–7) | 264 passed, 1 skipped |
| Regressão lain | 64 passed |

O teste pulado requer `cryptography` (não instalado) — criptografia em repouso opcional.

---

## Dados e isolamento

| Item | Local |
|------|-------|
| Banco do 2.0 | `ultron-2.0/data/ultron2.db` |
| Memória de fatos do 2.0 | `ultron-2.0/data/memory.json` |
| Banco original do usuário | `lain/ultron.db` — nunca tocado |
| Memória original do Mark-LVI | `Mark-LVI-main/memory/long_term.json` — nunca tocado |
| Credenciais | `lain/.env` (somente leitura) |

`Mark-LVI-main/config/api_keys.json` não existe e não deve ser criado.

---

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| `AGENTS.md` | Diretrizes mestras ULTRON 2.1 e roteiro de fases |
| `PROJECT_CONTEXT.md` | Visão global, identidade, origem, arquitetura, estado |
| `docs/context/CONTEXT_INDEX.md` | Índice de conhecimento |
| `docs/context/TECHNICAL_DECISIONS.md` | ADRs 001–018 |
| `docs/context/DEVELOPMENT_STATE.md` | Estado técnico real |
| `docs/context/MODULE_MAP.md` | Mapa dos módulos reais |
| `docs/ARCHITECTURE.md` | Arquitetura implementada |
| `docs/TESTING.md` | Testes, resultados e limitações |
| `docs/MEMORY.md` | Especificação de memória |
| `docs/CONTEXT.md` | Especificação de contexto |
| `docs/INTERFACE.md` | Especificação da interface |
| `docs/ui/` | Auditoria, arquitetura, componentes, matriz, testes de UI |
| `docs/MODEL_ROUTER.md` | Model Router (Fase 3) |
| `docs/AGENTES.md` | Multiagente (Fase 4) |
| `docs/INTEGRACOES.md` | CLI/MCP (Fase 5) |
| `docs/MEMORIA.md` | Evolução da memória (Fase 6) |
| `docs/AUTONOMIA.md` | Autonomia operacional (Fase 7) |
| `docs/roadmap/ULTRON_21_FINAL_REPORT.md` | Relatório final (Fase 8) |

---

## Repositórios

- **Raiz (`/home/marcelo/projetos/ultron/`):** specs e documentação (Git próprio).
- **`ultron-2.0/`:** código e testes (Git próprio, ignorado na raiz por decisão de ADR-011).
- **`lain/`:** núcleo original (somente leitura, não versionado aqui).
- **`Mark-LVI-main/`:** infraestrutura operacional (somente leitura, não versionado aqui).

Remote configurado: `origin` → `https://github.com/Marcelo-DevPythonSec23/ultron.git` (repositório da raiz, specs e documentação).

---

## Restrições de segurança

- Não modificar `lain/` nem `Mark-LVI-main/`.
- Nunca expor `GEMINI_API_KEY`.
- Todas as ferramentas passam pelo `ToolGateway` (allowlist, validação, timeout, autorização).
- Ações destrutivas exigem confirmação explícita (`AuthorizationManager`).
- Resultados de agentes/ferramentas externos são dados não confiáveis.

---

## Limitações conhecidas

- Wake word / VAD / barge-in não implementados.
- Busca semântica com embeddings é opcional (`sentence-transformers` não instalado).
- Criptografia em repouso é opcional (`cryptography` não instalada).
- Testes de integração ao vivo com Gemini dependem de rede e quota da API.
- A interface desktop requer bibliotecas do sistema Qt (`libxcb-cursor0` etc.) para exibição em modo janela; funciona em modo offscreen para desenvolvimento.
