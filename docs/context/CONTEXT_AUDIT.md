# CONTEXT_AUDIT — auditoria do conhecimento disponível

**Data:** 2026-11-10
**Escopo:** `lain/docs/`, `Mark-LVI-main/readme.md`, `Mark-LVI-main/AGENTS.md`,
`ultron-2.0/AGENTS.md`, `ultron-2.0/README.md`, `docs/*.md`, código e testes dos
três diretórios.
**Regra:** este documento separa **fato verificado no código**, **fato
documentado**, **decisão aprovada**, **inferência** e **lacuna**. Nada aqui foi
inventado; quando a evidência é parcial, está marcado.

---

## 1. Contexto atualmente disponível

| Fonte | Volume | Estado | Autoridade |
|---|---|---|---|
| `docs/INTEGRATION_AUDIT.md` | ~600 linhas | atual (2026-11-10) | **máxima** para a integração |
| `docs/ARCHITECTURE.md` | 203 linhas | atual | arquitetura implementada |
| `docs/INTEGRATION_MAP.md` | 101 linhas | atual | mapa de reutilização |
| `docs/VOICE_PIPELINE.md` | 96 linhas | atual | voz |
| `docs/TOOLS.md` | 135 linhas | atual | ferramentas |
| `docs/SECURITY.md` | 115 linhas | atual | segurança |
| `docs/TESTING.md` | 83 linhas | atual | testes |
| `lain/docs/**` | 13 documentos | históricos (pré-integração) | válidos para o núcleo |
| `Mark-LVI-main/readme.md` | 1.700+ linhas | histórico do runtime | referência do Mark-LVI |
| `ultron-2.0/README.md` | 151 linhas | atual | uso real |
| `docs/archive/INTEGRATION_AUDIT.draft-v1.md` | rascunho | **substituído** | não usar como verdade |

## 2. Documentações encontradas (por diretório)

### 2.1 `lain/docs/`

- `architecture/software_architecture_document.md` — Clean Architecture,
  camadas `api/core/intelligence/database/models`.
- `architecture/component_responsibility_matrix.md` — matriz de
  responsabilidades por arquivo.
- `architecture/database_model.md` — ERD `conversations`/`messages`.
- `architecture/dependency_diagram.md` — regra de dependência.
- `architecture/system_data_flow.md` — sequência do chat.
- `architecture/api_contract.md` — contrato REST do lain.
- `decisions/ADR-001..004` — modular, provider abstraction, async sqlite,
  FastAPI/Pydantic.
- `development/mvp_scope.md`, `development_roadmap.md`,
  `development/security_and_quality_audit.md`.

**Observação:** o roadmap interno do lain (`development_roadmap.md`) marca
Fases 3–7 como “Pendente”, mas o código e os 64 testes provam que o MVP está
implementado. **Documento desatualizado**, não contradição de código.

### 2.2 `Mark-LVI-main/`

- `readme.md` — manual extenso do runtime original.
- `AGENTS.md` — regras do runtime (threads, TOOL contract, confirmação).
- Código: `main.py`, `core/`, `actions/`, `providers/`, `memory/`.
- **Não há `docs/`**: o readme é a fonte principal.

### 2.3 `ultron-2.0/`

- `AGENTS.md` — master prompt da integração (fonte de requisitos).
- `README.md` — instalação, uso e estado real.
- `docs/` do 2.0 **não existe**; a documentação vive na raiz `docs/`.

## 3. Informações arquiteturais identificadas (confirmadas no código)

1. O `Orchestrator` do lain é o **único** ciclo de conversa (fato de código:
   `ultron_2_0/core_runtime.py` instancia `app.core.orchestrator.Orchestrator`).
2. `LLMRequest` do lain **não tem campo `tools`**; tool calling é extensão do
   2.0 via `ToolCallingProvider` (`ultron_2_0/tool_loop.py`) sob o mesmo
   `provider_id`.
3. `ToolGateway` valida allowlist, parâmetros, timeout e confirmação
   (`ultron_2_0/tool_gateway.py`).
4. Banco isolado: `ultron-2.0/data/ultron2.db` (`bootstrap.default_database_url`).
5. Memória de fatos: `ultron-2.0/data/memory.json`, via
   `Mark-LVI-main/memory/memory_manager.py` reutilizado (`memory_tools.py`).
6. Voz: STT Gemini Live **somente transcrição** + TTS Gemini/voz do sistema;
   o texto entra em `OrchestratorBridge.process_text` (`voice/pipeline.py`).
7. TTS exige `api_version="v1beta"` no `google-genai 3.0.0` (bug real corrigido
   em 2026-11-10; evidência em `docs/TESTING.md`).
8. HUD web: FastAPI/uvicorn em `127.0.0.1:8765`, sobre o mesmo bridge.
9. `core/stt.py` e `core/tts.py` do Mark-LVI são **código morto** (nenhum
   import); não foram usados.

## 4. Decisões confirmadas

As decisões nº 1–6 e o plano por etapas estão em
`docs/INTEGRATION_AUDIT.md`. Resumo:

| # | Decisão | Evidência |
|---|---|---|
| 1 | `google-genai 3.0.0` no 2.0 | `requirements.txt`, `tests/test_bootstrap.py` |
| 2 | Núcleo lain por composição, sem cópia | `core_runtime.py` |
| 3 | Subset curado de actions | `marklvi_actions.py`, `gateway.names()` |
| 4 | Tool calling por protocolo JSON | `tool_loop.py`, `docs/TOOLS.md` |
| 5 | Venv dedicado | `.venv/`, README |
| 6 | HUD web em vez de Qt | `web/`, decisão na auditoria |

## 5. Informações contraditórias encontradas

| Contradição | Fontes | Resolução |
|---|---|---|
| “Fases 2–7 do lain pendentes” | `lain/docs/development/development_roadmap.md` | **código + 64 testes** vencem; documento é histórico |
| “Mark-LVI tem STT/TTS em `core/`” | `ultron-2.0/AGENTS.md` §2, `docs/INTEGRATION_AUDIT.md` §2.3 | auditoria verificou que são mortos; README do 2.0 reflete o real |
| Contagem de testes 151 vs 87 vs 88 | AGENTS.md, versões anteriores de TESTING/README | suíte atual medida: **88** no 2.0 + **64** no lain |
| `MARKLVI_ROOT` sem `/memory` na doc antiga | `docs/archive` | audit atual confirma `memory/` existe |

Nenhuma foi resolvida silenciosamente: todas estão registradas aqui e nos
documentos afetados.

## 6. Lacunas de conhecimento

1. Não há benchmark de latência/consumo de tokens do 2.0.
2. Não há avaliação empírica da qualidade do `recall` lexical.
3. Não há teste ao vivo automatizado de STT Live (depende de microfone/rede).
4. `wake word`, `VAD`, `barge-in` não existem no 2.0.
5. Não há interface de confirmação interativa; `forget` é recusado.
6. Não há memória automática/consolidação integrada ao turno (apenas tools
   explícitas). Ver `docs/memory/`.
7. `Mark-LVI-main` não é repositório git; não há histórico de commits dele.
8. `lain/` tem alteração preexistente em `.env.example` (do usuário).

## 7. Documentos obsoletos ou substituídos

- `docs/archive/INTEGRATION_AUDIT.draft-v1.md` — rascunho, substituído pelo
  `INTEGRATION_AUDIT.md`.
- `lain/docs/development/development_roadmap.md` — estados de fase
  desatualizados.
- `lain/docs/development/mvp_scope.md` — lista tool calling como “fora do
  escopo”; no 2.0 ele é fornecido pela camada de integração, não pelo lain.
- `ultron-2.0/AGENTS.md` cita arquivos de áudio do Mark-LVI que a auditoria
  provou mortos; mantido como prompt histórico, com a ressalva em
  `docs/INTEGRATION_AUDIT.md`.

## 8. Fontes de informação mais confiáveis

1. **Código + testes em execução** (evidência primária).
2. `docs/INTEGRATION_AUDIT.md` (decisões e riscos).
3. `docs/ARCHITECTURE.md`, `INTEGRATION_MAP.md`, `VOICE_PIPELINE.md`,
   `TOOLS.md`, `SECURITY.md`, `TESTING.md`.
4. `ultron-2.0/README.md`.
5. `lain/docs/decisions/ADR-*` (decisões do núcleo).
6. `Mark-LVI-main/AGENTS.md` (restrições do runtime original).
7. Documentos históricos e rascunhos — somente com checagem.

## 9. Recomendações para organização do contexto

1. Manter `PROJECT_CONTEXT.md` como porta de entrada e
   `docs/context/CONTEXT_INDEX.md` como mapa.
2. Não duplicar arquitetura: `docs/ARCHITECTURE.md` continua sendo a fonte;
   `ARCHITECTURE_CONTEXT.md` resume e aponta.
3. Registrar toda decisão nova em `TECHNICAL_DECISIONS.md`.
4. Atualizar `DEVELOPMENT_STATE.md` somente com evidência (arquivo/teste).
5. Não promover hipótese a fato: usar as marcas `FATO`, `DOC`, `DECISÃO`,
   `INFERÊNCIA`, `LACUNA`.
6. Validar caminhos documentais com teste automatizado
   (`ultron-2.0/tests/test_docs.py`).

---

## Rastreabilidade

- Fatos de código: `ultron-2.0/ultron_2_0/*`, testes em `ultron-2.0/tests/*`.
- Execução: `./.venv/bin/python -m pytest -q` → 88 passed; `lain` → 64 passed.
- Validação ao vivo: Gemini texto, TTS Gemini, HUD HTTP (ver `docs/TESTING.md`).
- Nenhum repositório original foi modificado na auditoria.
