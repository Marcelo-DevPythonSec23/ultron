# TECHNICAL_DECISIONS — registro de decisões arquiteturais (ADR)

Formato inspirado em ADRs. Quando a decisão foi inferida (não registrada
explicitamente pelo usuário), está marcada **INFERÊNCIA**. Datas: as decisões
originais da integração foram tomadas na auditoria de 2026-11-10.

---

## ADR-001 — Orquestrador central no núcleo ULTRON

**Status:** Aceita
**Contexto:** existem dois projetos com ciclos conversacionais próprios.
**Problema:** dois assistentes disputariam a conversa e o histórico.
**Alternativas:** (a) Mark-LVI como núcleo; (b) núcleo novo; (c) ULTRON como
núcleo e Mark-LVI como corpo.
**Decisão:** o `Orchestrator` do `lain/` é o único ciclo de conversa; o 2.0 o
instancia sem modificá-lo.
**Justificativa:** preserva personalidade, contexto, providers e histórico já
validados (64 testes).
**Consequências:** toda interface chama `OrchestratorBridge.process_text`; o
runtime Mark-LVI não é executado.
**Fontes:** `docs/INTEGRATION_AUDIT.md`, `ultron_2_0/core_runtime.py`.

---

## ADR-002 — Importar os originais, nunca copiar

**Status:** Aceita
**Contexto:** regra de não modificar `lain/` e `Mark-LVI-main/`.
**Decisão:** `bootstrap.ensure_sys_paths()` adiciona os diretórios ao `sys.path`;
dados do 2.0 são isolados.
**Consequências:** sem cópias divergentes; correções nos originais exigem
revisão. `lain/ultron.db` e `long_term.json` intocados.
**Fontes:** `bootstrap.py`, `test_memory_tools.py`.

---

## ADR-003 — Tool calling como extensão do 2.0, não do lain

**Status:** Aceita
**Contexto:** `LLMRequest` do lain não possui `tools` e não deve ser alterado.
**Decisão:** `ToolCallingProvider` envolve qualquer `LLMProvider` sob o mesmo
`provider_id`, usando protocolo JSON no prompt; `ToolGateway` executa.
**Consequências:** o orquestrador do lain não percebe a extensão; ferramentas
são validadas fora do modelo. Custo: uma chamada extra ao modelo por tool.
**Fontes:** `tool_loop.py`, `docs/TOOLS.md`, `test_tool_loop.py`.

---

## ADR-004 — Subset curado de actions do Mark-LVI

**Status:** Aceita
**Contexto:** 21 actions, várias com `shell=True`, `pyautogui` sem failsafe e
chaves próprias.
**Decisão:** apenas `system_status`, `open_app`, `web_search`, `reminder`.
**Justificativa:** utilidade real com risco controlado; sem shell arbitrário.
**Consequências:** actions de escrita/execução ficam `BLOCKED` até revisão.
**Fontes:** `marklvi_actions.py`, `docs/SECURITY.md`, `INTEGRATION_MAP.md`.

---

## ADR-005 — `google-genai 3.0.0` e TTS em `v1beta`

**Status:** Aceita
**Contexto:** núcleo usa 3.0.0; Mark-LVI pedia `<3`; TTS falhava com
`Unknown name "speechConfig"`.
**Decisão:** manter 3.0.0 no 2.0 e criar o cliente de TTS com
`http_options={"api_version": "v1beta"}`.
**Evidência:** validação ao vivo gerou 167.566 bytes PCM a 24 kHz; em `v1` a API
responde 400.
**Consequências:** TTS funciona; o runtime Mark-LVI continua não executado.
**Fontes:** `voice/tts.py`, `test_voice_units.py`, `docs/TESTING.md`.

---

## ADR-006 — HUD web em vez de Qt

**Status:** Aceita
**Contexto:** ~4 GB RAM; PyQt6 não instalado; FastAPI/uvicorn já presentes.
**Decisão:** HUD local FastAPI em `127.0.0.1:8765`.
**Consequências:** sem stack nova pesada; bind local por padrão; sem CDN.
**Fontes:** `web/`, `test_web.py`, `SECURITY.md`.

---

## ADR-007 — Memória de fatos explícita, reusando o manager do Mark-LVI

**Status:** Aceita
**Contexto:** o gerenciador do Mark-LVI tem categorias, atualização e busca
lexical; o 2.0 precisa de memória própria sem duplicar histórico.
**Decisão:** reutilizar `memory_manager` apontando `MEMORY_PATH` para
`data/memory.json`; nada é salvo automaticamente.
**Consequências:** `forget` exige confirmação (recusado sem UI); evolução para
motor tipado está em `docs/memory/`.
**Fontes:** `memory_tools.py`, `test_memory_tools.py`.

---

## ADR-008 — Voz é interface; STT só transcreve

**Status:** Aceita
**Contexto:** o loop Gemini Live do Mark-LVI também raciocina e chama tools.
**Decisão:** abrir o Live apenas para transcrição (`response_modalities=["TEXT"]`
+ `input_audio_transcription`), sem tools; o texto segue ao mesmo bridge.
**Consequências:** um único histórico; sem wake word/VAD/barge-in (não existem).
**Fontes:** `voice/stt_gemini.py`, `voice/pipeline.py`.

---

## ADR-009 — Memória como subsistema do Core (Memory Engineering)

**Status:** Aceita (implementação incremental)
**Contexto:** `MEMORY.md` pede tipos, retrieval, versionamento, consolidação,
orçamento e segurança.
**Decisão:** criar `MemoryEngine` como fachada sobre o armazenamento real
(`memory_manager`), sem segundo cérebro e sem banco novo.
**Consequências:** tipos mapeados para categorias + sessões; novas capacidades
só quando validadas por teste. Ver `docs/memory/MEMORY_ARCHITECTURE.md`.
**Fontes:** `memory_tools.py`, `docs/memory/`.

---

## ADR-010 — Nenhum Model Router fictício

**Status:** Aceita
**Contexto:** AGENTS.md §8 pede desacoplamento, mas proíbe roteador fictício.
**Decisão:** manter o `ProviderRegistry` do lain como autoridade; seleção por
`provider`/`model` na requisição. Roteamento automático fica `PLANNED`.
**Fontes:** `core_runtime.py`, `docs/ARCHITECTURE.md`.

---

## Modelo para novas decisões

```markdown
## ADR-XXX — Título
**Status:** Proposta | Aceita | Substituída por ADR-YYY | Rejeitada
**Contexto:** ...
**Problema:** ...
**Alternativas:** ...
**Decisão:** ...
**Justificativa:** ...
**Consequências:** ...
**Fontes:** ...
```
