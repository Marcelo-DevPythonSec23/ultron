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

**Status:** Substituída por ADR-014
**Contexto:** AGENTS.md §8 pede desacoplamento, mas proíbe roteador fictício.
**Decisão (original):** manter o `ProviderRegistry` do lain como autoridade; seleção por
`provider`/`model` na requisição. Roteamento automático fica `PLANNED`.
**Substituição:** ADR-014 implementa o `ModelRouter` real (Fase 3) envolvendo o
`ProviderRegistry` sem modificá-lo.
**Fontes:** `core_runtime.py`, `docs/ARCHITECTURE.md`.

---

## ADR-011 — Documentação da raiz em repositório Git próprio

**Status:** Aceita (2026-11-11)
**Contexto:** specs (`AGENTS.md`, `CONTEXT.md`, `MEMORY.md`, `INTERFACE.md`) e
`docs/` viviam fora do Git; só `ultron-2.0/` e `lain/` eram repositórios.
**Problema:** contexto e decisões se perderiam entre sessões/agentes.
**Alternativas:** (a) copiar docs para `ultron-2.0/`; (b) repositório na raiz;
(c) submódulo.
**Decisão:** repositório Git na raiz versionando specs e `docs/`, com
`.gitignore` para `lain/`, `Mark-LVI-main/`, `ultron-2.0/`, dados e segredos.
**Justificativa:** preserva os originais, mantém cada código no seu repo e não
duplica documentação.
**Consequências:** documentação nova entra no repo da raiz; código/testes no
repo do produto. Commit inicial `3fb03bb`.
**Fontes:** `.gitignore`, `docs/context/CONTEXT_INDEX.md`.

---

## ADR-012 — Autorização interativa separada da execução

**Status:** Aceita (2026-11-11)
**Contexto:** `requires_confirmation` existia, mas o gateway recusava sempre;
não havia como confirmar pela CLI/HUD.
**Decisão:** `AuthorizationManager` (`ultron_2_0/authorization.py`) com
`PendingAction` + `ApprovalToken` de uso único, vinculado a ferramenta +
argumentos exatos (SHA-256), com expiração; a aprovação vem da interface, nunca
do modelo; a execução só ocorre com token válido e consumido.
**Consequências:** `forget` passou a funcionar (e revelou que ele buscava apenas
o escopo `global`, enquanto fatos do usuário nascem em `user:default` — corrigido
para os escopos de leitura); replay/argumentos alterados são rejeitados;
auditoria registra pedido, aprovação e execução. Voz sempre recusa.
**Evidência:** `tests/test_authorization.py` (14), `test_web.py` (aprovações),
`test_integration_tools.py` (forget aprovado/recusado), 128 testes verdes.
**Fontes:** `tool_gateway.py::_authorize`, `SECURITY.md`, `TOOLS.md`.

---

## ADR-013 — Fase 2.5 adapta a interface ao HUD web

**Status:** Aceita (Fase 2.5 implementada)
**Contexto:** a referência Mark-LVI é PyQt6 (`ui.py`, 7.504 linhas, avatar,
viseme) mais um dashboard HTTPS; o ambiente tem ~4 GB RAM e o 2.0 já tem HUD
web (ADR-006).
**Decisão:** auditar a referência e reconstruir a **funcionalidade** no HUD web,
com identidade ULTRON própria, sem portar PyQt6. HUD local (`127.0.0.1`); voz em
processo separado; dashboard remoto, plugins e edição direta de memória não
portados por segurança/escopo.
**Consequências:** paridade funcional documentada por matriz
(`docs/ui/UI_FUNCTIONALITY_MATRIX.md`); diferenças de plataforma registradas;
métricas e atividade vêm de fontes reais; animações respeitam
`prefers-reduced-motion`.
**Evidência:** `docs/ui/` (5 documentos), `web/activity.py`,
`marklvi_actions.system_snapshot`, `test_web.py` (21), 136 testes verdes.
**Fontes:** `INTERFACE.md`, `ultron_2_0/web/`.

---

## ADR-014 — Model Router (Fase 3)

**Status:** Aceita
**Contexto:** o ULTRON precisa coordenar múltiplos provedores de IA, selecionar
o modelo conforme o tipo de tarefa e aplicar fallback com timeout/retry, sem
criar um segundo orquestrador conversacional nem expor credenciais.
**Alternativas:** (a) substituir o `ProviderRegistry` do lain; (b) envolver o
registry com uma camada de seleção/encaminhamento (duck typing); (c) roteador
fictício sem execução real (rejeitado por AGENTS.md §8).
**Decisão:** (b) — criar `ModelRouter` em `ultron_2_0/routing/` que envolve o
`ProviderRegistry` existente (continua sendo a autoridade de registro) e é
passado ao `Orchestrator` no lugar do registry. Componentes: `ModelRouter`,
`RouterConfig`, `RoutingProvider`, `ModelCatalog`, `ModelCapabilities`,
`TaskType`, `infer_task_type`, `ModelSelectionPolicy`, `Candidate`,
`ProviderAdapter`, `FallbackManager`, `RetryManager`, `RetryPolicy`,
`MetricsRegistry`. Componentes reais do contrato `LLMProvider` são usados
(`StubProvider` em testes, `mock`/`gemini` em produção) — sem roteador fictício.
**Regras de projeto:**
- o provedor padrão continua sendo o primário; a política ordena os demais
  apenas como fallback;
- fallback entre provedores é **opt-in** (`ULTRON_ROUTER_FALLBACK`, default 0)
  — trocar silenciosamente de provedor muda custo/privacidade;
- `mock` nunca é fallback automático (`allow_mock_fallback`);
- provedor/modelo escolhidos explicitamente são respeitados e desligam o
  fallback daquele turno;
- em `mode="auto"` (opt-in via `ULTRON_ROUTER_MODE`), a política escolhe o
  provedor por tipo de tarefa e `RoutingProvider.default_model` retorna o
  sentinela `"auto"`; o modelo real é escolhido por tarefa e gravado na
  mensagem do assistente;
- retry classifica transitórios (rate limit/unavailable/timeout/connection/
  response) como repetíveis e definitivos (auth/access/invalid/not found) como
  não repetíveis; a última exceção é propagada sem embrulho;
- overrides de modelo por tarefa (`model_overrides`) são decisões explícitas
  do catálogo, não dependem de empate de score;
- métricas e snapshots nunca expõem credenciais (sanitização de erros).
**Justificativa:** desacoplamento de provedor sem acoplar o núcleo a um único
fornecedor; `ProviderRegistry` preservado; fallback é explícito, não oculto;
tempo de execução e falhas isoladas por provedor.
**Consequências:** `core_runtime.py` cria `ModelRouter(self.registry)` e passa
`provider_registry=self.router` ao `Orchestrator`; `register_provider` delega
ao router; `orchestrator_bridge.py` expõe `router_config` e
`status()["router"]`; CLI exibe estado do roteador; `default_model` no modo
`auto` retorna `"auto"`.
**Evidência:** `tests/test_routing.py` (41 testes: 36 originais + 5 do modo
`auto`), suíte 2.0 com **177 passed**, regressão lain **64 passed**,
`secret_leak: False` no smoke de status.
**Fontes:** `ultron_2_0/routing/`, `tests/test_routing.py`,
`tests/fakes.py` (`StubProvider`), `ultron_2_0/core_runtime.py`,
`ultron_2_0/orchestrator_bridge.py`, `ultron_2_0/cli.py`,
`docs/MODEL_ROUTER.md`.

---

## ADR-015 — Sistema Multiagente (Fase 4)

**Status:** Aceita
**Contexto:** o ULTRON precisa coordenar agentes especializados e delegar
tarefas, preservando-se como a única autoridade de conversação, memória e
orquestração, sem criar um segundo orquestrador conversacional.
**Alternativas:** (a) criar um segundo ciclo conversacional independente
(rejeitado por AGENTS.md §3.2 — disputaria autoridade com o núcleo);
(b) camada de coordenação de agentes sobre o núcleo existente (duck typing,
sem tocar no histórico/memória/process_text).
**Decisão:** (b) — criar pacote `ultron_2_0/agents/` com `AgentOrchestrator`
(autoridade central de coordenação), `AgentRegistry` (registro e descoberta),
`AgentTask`/`AgentResult`/`AgentCapability`/`TaskState` (contratos
estruturados), `TaskQueue` (fila com isolamento de arquivos para concorrência),
`AgentValidator`+`ResultManager` (validação de resultados não confiáveis),
`ExecutionMonitor` (observabilidade), e 6 agentes iniciais como adaptadores
sobre ferramentas existentes (Developer, Research, Security, QA, Database,
Architecture) — não modelos próprios para o que já existe.
**Regras de projeto:**
- responsabilidades delimitadas por agente;
- isolamento de contexto por tarefa;
- contratos estruturados (`AgentTask`/`AgentResult`);
- resultados enviados ao ULTRON para avaliação centralizada;
- agentes não modificam memória canônica sem autorização (Fase 2);
- isolamento de arquivos em tarefas concorrentes (`TaskQueue`);
- identificação de origem em todo resultado;
- falhas detectadas e registradas (replanejamento com `max_attempts`);
- exceções de agente não derrubam o núcleo;
- primeira implementação utiliza agentes externos existentes quando viável
  (Fase 5: OpenCode, Claude Code, MCP).
**Justificativa:** coordenação de inteligência externa sem perder a autoridade
central do ULTRON; isolamento e rastreabilidade; resultados não confiáveis até
validar; compatibilidade com o `ProviderRegistry` (Fase 3) preservada.
**Consequências:** `core_runtime.py` cria `AgentOrchestrator(max_concurrent=3)`
e registra os 6 agentes iniciais; `orchestrator_bridge.py` expõe
`status()["agents"]`; `AgentOrchestrator` não toca no histórico, memória
canônica nem `process_text`.
**Evidência:** `tests/test_agents.py` (19 testes), suíte 2.0 com **196 passed**,
regressão lain **64 passed**, `secret_leak` equivalente no status do bridge.
**Fontes:** `ultron_2_0/agents/`, `tests/test_agents.py`,
`ultron_2_0/core_runtime.py`, `ultron_2_0/orchestrator_bridge.py`,
`docs/AGENTES.md`.

---

## ADR-016 — Integrações externas: agentes CLI e MCP (Fase 5)

**Status:** Aceita
**Contexto:** o ULTRON precisa se conectar a agentes/servidores externos
(OpenCode CLI, servidores MCP) sem perder o controle central do fluxo de
execução, respeitando a regra de não criar um segundo orquestrador
conversacional.
**Alternativas:** (a) incorporar cada agente externo diretamente no núcleo
(rejeitado — acoplamento e risco); (b) adaptadores independentes sobre as
interfaces reais de cada ferramenta, processos isolados com timeout e controle
de permissões por integração.
**Decisão:** (b) — criar pacote `ultron_2_0/integrations/` com
`IntegrationOrchestrator` (coordena tarefas), `IntegrationRegistry` (registro,
habilitar/desabilitar por target), `ExternalIntegration` (subprocesso isolado
sem shell=True, timeout com `asyncio.wait_for`, `sanitize_output`),
`OpenCodeAdapter` (interface real `opencode run [--format json] ...`) e
`MCPAdapter` (interface real `opencode mcp list`).
**Regras de projeto:**
- inspecionar interfaces reais; não inventar comandos, APIs ou contratos;
- adaptadores independentes por integração;
- processos externos isolados (subprocesso, nunca shell=True);
- limites de execução (timeout por integração);
- registrar tarefas e resultados (`IntegrationTask`/`IntegrationResult`);
- controle de permissões por integração (habilitar/desabilitar individualmente);
- permitir desativar cada integração individualmente;
- resultados de agentes externos são dados não confiáveis até validar;
- não aplicar resultados automaticamente à memória canônica.
**Justificativa:** conexão com inteligência externa sem perder a autoridade
central do ULTRON; isolamento de processos externos; falhas de integração não
derrubam o núcleo; compatibilidade com o `ProviderRegistry` (Fase 3) e com o
`AgentOrchestrator` (Fase 4) preservadas.
**Consequências:** `core_runtime.py` cria `IntegrationOrchestrator()` e
registra `OpenCodeAdapter()` + `MCPAdapter()`; `orchestrator_bridge.py` expõe
`status()["integrations"]`; `IntegrationOrchestrator` não toca no histórico,
memória canônica nem `process_text`.
**Evidência:** `tests/test_integrations.py` (19 testes), suíte 2.0 com
**215 passed**, regressão lain **64 passed**, status sem credenciais.
**Fontes:** `ultron_2_0/integrations/`, `tests/test_integrations.py`,
`ultron_2_0/core_runtime.py`, `ultron_2_0/orchestrator_bridge.py`,
`docs/INTEGRACOES.md`.

---

## ADR-017 — Evolução da Memória (Fase 6)

**Status:** Aceita
**Contexto:** o `MemoryEngine` já existia com busca léxica, versionamento,
expiração, tombstone e isolamento de escopos. A Fase 6 expande a recuperação
e o relacionamento de informações sem tornar embeddings/criptografia/backup
dependências obrigatórias e sem alterar o `MemoryEngine` existente.
**Alternativas:** (a) adicionar embeddings como dependência obrigatória
(rejeitado — AGENTS.md §4.6 proíbe); (b) extensões opcionais que desativam
graciosamente quando a dependência está ausente.
**Decisão:** (b) — criar `memory_semantic.py` (`SemanticIndex`, busca semântica
opcional via `sentence-transformers`), `memory_backup.py` (`backup_memory`/
`restore_memory`, ZIP com manifesto sem expor conteúdo), `memory_encryption.py`
(`MemoryEncryption`, criptografia opcional em repouso com `cryptography.fernet`,
chave nunca exposta) e adicionar métodos ao `MemoryEngine`
(`search_semantic`, `retrieve_hybrid`, `backup`, `restore`, `encryption_status`,
`encrypt_memory_file`, `decrypt_memory_file`) sem alterar contratos existentes.
**Regras de projeto:**
- embeddings NÃO são dependência obrigatória (desativam graciosamente);
- criptografia NÃO é dependência obrigatória (chave nunca exposta);
- backup não destrutivo (só lê); restauração requer `confirm=True`;
- consolidação continua somente leitura (não reescreve nem apaga fatos);
- exclusão autorizada e isolamento de escopos preservados;
- recuperação lexical preservada (`MemoryEngine.search` inalterado).
**Justificativa:** expansão de recuperação e relacionamento de informações sem
quebrar a memória existente nem impor dependências externas; falhas de
dependência opcional não comprometem o núcleo.
**Consequências:** `memory_engine.py` importa os 3 novos módulos e adiciona
métodos Fase 6; `search_semantic`/`retrieve_hybrid` caem de volta para a busca
léxica sem embeddings; `docs/MEMORIA.md` documenta a fase.
**Evidência:** `tests/test_memory_phase6.py` (16 testes), suíte 2.0 com
**231 passed**, regressão lain **64 passed**, compatibilidade com memória
existente preservada (17 testes de `test_memory_engine.py` verdes).
**Fontes:** `ultron_2_0/memory_semantic.py`, `ultron_2_0/memory_backup.py`,
`ultron_2_0/memory_encryption.py`, `ultron_2_0/memory_engine.py`,
`tests/test_memory_phase6.py`, `docs/MEMORIA.md`.

---

## ADR-018 — Autonomia Operacional (Fase 7)

**Status:** Aceita
**Contexto:** o ULTRON precisa planejar e executar fluxos de trabalho complexos,
sem criar um segundo orquestrador conversacional que dispute autoridade com o
núcleo (AGENTS.md §3.2).
**Alternativas:** (a) criar um segundo ciclo conversacional/planejador
independente (rejeitado — competiria com o orquestrador); (b) pacote de
autonomia que decompõe objetivos e delega passos aos orquestradores existentes
(AgentOrchestrator Fase 4, IntegrationOrchestrator Fase 5), sem tocar no
histórico/memória/process_text.
**Decisão:** (b) — criar pacote `ultron_2_0/autonomy/` com `Planner` (planeja
Workflow a partir de objetivo), `TaskDecomposer` (decomposição determinística),
`WorkflowEngine` (executa delegando aos orquestradores existentes),
`StateTracker` (persiste estado para recuperação), `Scheduler` (agenda por
horário), `RecoveryManager` (plana recuperação de FAILED/PAUSED) e contratos
de dados (`Workflow`, `WorkflowStep`, `WorkflowState`, `StepState`,
`StepDependency`).
**Regras de projeto:**
- separar planejamento de execução (Planner apenas planeja, Engine executa);
- limites de recursos e tempo (max_steps, max_execution_seconds);
- autorização para operações sensíveis (require_human_approval);
- registrar decisões e resultados (StateTracker, ExecutionMonitor);
- evitar loops (dependências lineares, estados bem definidos);
- limites de tentativas por passo (max_attempts, replanejamento);
- preservar interrupção humana (estado PAUSED, retry/skip de passo);
- não executar código gerado por modelos (segurança: AGENTS.md §3.3).
**Justificativa:** autonomia progressiva sem perder a autoridade central do
ULTRON; falhas de passo não derivam em falha imediata do workflow se houver
tentativas; recuperação após falhas e retomada de trabalhos interrompidos.
**Consequências:** `core_runtime.py` pode criar `WorkflowEngine` (opcional,
com AgentOrchestrator e IntegrationOrchestrator); `orchestrator_bridge.py`
expõe estado de autonomia via `status()`; `WorkflowEngine` não toca no
histórico, memória canônica nem `process_text`.
**Evidência:** `tests/test_autonomy.py` (21 testes), suíte 2.0 com
**252 passed**, regressão lain **64 passed**.
**Fontes:** `ultron_2_0/autonomy/`, `tests/test_autonomy.py`,
`docs/AUTONOMIA.md`.

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
