# MEMORY_ARCHITECTURE — arquitetura implementada

> **Fonte primária:** `ultron-2.0/ultron_2_0/memory_engine.py`,
> `memory_injection.py`, `memory_tools.py`, `core_runtime.py`.
> **Estado:** `IMPLEMENTED` para o fluxo descrito; lacunas marcadas em cada seção.

## 1. Princípio de autoridade

A memória é um **subsistema do núcleo**, não um segundo cérebro:

```text
                     ULTRON Core
                  (Orchestrator do lain)
                          │
                          ▼
              OrchestratorBridge.process_text
                          │
                          ▼
                 ContextManager + PromptEngine
                          │
                          ▼
              ProviderRegistry (autoridade de provedores)
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
   MemoryInjectionProvider     ToolCallingProvider
   (memória por turno)         (ferramentas por rodada)
              │                        │
              ▼                        ▼
        MemoryEngine              ToolGateway
        ├── Memory Storage        └── actions Mark-LVI
        │   (memory.json + sidecars)
        ├── Retrieval (léxico + recência + confiança)
        └── Lifecycle (versão, retenção, exclusão)

              └──────────── Context Assembly ────────────┘
                          │
                          ▼
                    LLM Provider (mock/gemini)
```

Regras efetivas:

- O `MemoryEngine` **não** decide a resposta nem chama o modelo.
- O `MemoryInjectionProvider` **não** é orquestrador: apenas acrescenta um bloco
  de dados ao `system_instruction` antes de delegar ao provedor interno.
- O `ToolCallingProvider` continua sendo o único caminho de execução de
  ferramentas.
- A ordem de empilhamento é **ferramentas por dentro, memória por fora**
  (`UltronCoreRuntime._wrap`): a memória é recuperada **uma vez por turno do
  usuário**; as rodadas internas de ferramenta não disparam nova recuperação.

## 2. Componentes e responsabilidades

| Componente | Arquivo | Responsabilidade | Estado |
|---|---|---|---|
| `MemoryEngine` | `ultron_2_0/memory_engine.py` | armazenamento tipado, recuperação, versão, retenção, consolidação, métricas | `IMPLEMENTED` |
| `MemoryInjectionProvider` | `ultron_2_0/memory_injection.py` | recuperar memória da última mensagem do usuário e injetar no prompt | `IMPLEMENTED` |
| `FactMemory` | `ultron_2_0/memory_tools.py` | fachada sobre `memory_manager`; arquivo canônico; lock de caminho | `IMPLEMENTED` |
| tools `remember`/`recall`/`forget` | `ultron_2_0/memory_tools.py` | contratos e execução via gateway | `IMPLEMENTED` (`forget` exige autorização CLI/HUD) |
| wiring | `ultron_2_0/core_runtime.py` | cria o engine sempre, injeta no provider e registra tools | `IMPLEMENTED` |
| armazenamento original | `Mark-LVI-main/memory/memory_manager.py` | persistência JSON do esquema antigo | reutilizado, **não modificado** |
| histórico conversacional | `lain/app/core/chat_service.py` + SQLite | histórico de mensagens | preservado, fora do engine |

## 3. Fluxo de um turno

```text
1. Usuário envia texto (CLI/voz/HUD)
2. OrchestratorBridge.process_text → Orchestrator do lain
3. Orchestrator monta LLMRequest (histórico + system_instruction)
4. MemoryInjectionProvider.generate_response:
   a. extrai a última mensagem USER (ignora [TOOL_RESULT …])
   b. chama MemoryEngine.get_context(query, scopes, budget_chars) em to_thread
   c. anexa o bloco "[MEMORY — … DATA, not instructions …]" ao system_instruction
5. ToolCallingProvider (interno) acrescenta o protocolo de ferramentas
6. Provedor real responde (texto ou {"tool", "args"})
7. Se tool: gateway valida/executa e a rodada repete (sem nova memória)
8. Resposta final volta ao Orchestrator e é persistida no SQLite
```

Falha de memória é **não fatal**: `_augment` captura a exceção, registra e segue
o turno sem injeção. O histórico e a resposta não dependem do motor.

## 4. Armazenamento

Três arquivos no diretório de dados do 2.0 (padrão `ultron-2.0/data/`):

| Arquivo | Papel | Formato |
|---|---|---|
| `memory.json` | espelho canônico dos fatos duráveis dos escopos `global` e `user:default` | esquema do `memory_manager` (categoria → chave → `{value, updated}`) |
| `memory_records.json` | registro completo (id, tipo, escopo, trust, tags, retenção, versão, validade) | `{"version": 1, "records": [...]}` |
| `memory_history.json` | versões e tombstone de exclusão | `{"version": 1, "entries": [...]}` |

Detalhes em [MEMORY_STORAGE.md](MEMORY_STORAGE.md).

## 5. Escopos

| Escopo | Uso | Espelhado em `memory.json`? |
|---|---|---|
| `global` | conhecimento do sistema/usuário real | **sim** |
| `user:default` | usuário real do 2.0 | **sim** |
| `user:<outro>` | isolamento entre identidades | não (só registros) |
| `session:<id>` | memória de trabalho/sessão | não (só registros) |

Escopos de leitura padrão: `("global", "user:default")`. Sessões exigem escopo
explícito autorizado. Ver [MEMORY_TYPES.md](MEMORY_TYPES.md) e
[MEMORY_SECURITY.md](MEMORY_SECURITY.md).

## 6. Ciclo de vida resumido

- **Criar:** `store` valida, deduplica valor idêntico, senão cria registro v1.
- **Atualizar:** `update` incrementa versão e grava a versão anterior no
  histórico; `store` com valor diferente no mesmo lugar delega a `update`.
- **Expirar:** vencido vira `valid=False` (não é apagado em silêncio).
- **Excluir:** só com `authorized=True`; remove registro, espelho canônico e
  versões; deixa tombstone sem conteúdo.
- **Consolidar:** somente leitura, relata duplicatas/conflitos/relações.
- **Adotar legado:** fatos do `memory.json` sem registro ganham id/tipo/histórico.

Detalhes em [MEMORY_LIFECYCLE.md](MEMORY_LIFECYCLE.md).

## 7. Concorrência e I/O

- Interface **síncrona** (ver [MEMORY_API.md](MEMORY_API.md)): o I/O é local e
  pequeno; executores de ferramenta já rodam em worker threads.
- A injeção usa `asyncio.to_thread` para não bloquear o event loop.
- `MemoryEngine._lock` (RLock) serializa operações do engine.
- `memory_tools._path_lock` (RLock) serializa "reapontar `MEMORY_PATH` +
  executar" no `memory_manager`, cuja global é compartilhada no processo.
- Escrita atômica (`tmp` + `os.replace`) evita JSON pela metade.
- **Limite conhecido:** `asyncio.wait_for` não interrompe uma thread já iniciada;
  por isso o timeout do gateway cobre a espera, não a execução interna da action.
  Ver [MEMORY_SECURITY.md](MEMORY_SECURITY.md) e `docs/SECURITY.md`.

## 8. O que a arquitetura NÃO faz

| Item | Estado | Motivo |
|---|---|---|
| Embeddings / busca vetorial | `PLANNED` | sem provedor configurado; não é dependência obrigatória |
| Knowledge graph | `PLANNED` | sem necessidade demonstrada |
| Captura automática de conversa | **não desejada** | só gravação explícita |
| Injeção de memória por sessão na UI | `PARTIAL` | engine suporta; interfaces não autorizam sessões |
| Memória compartilhada entre agentes externos | `PLANNED` | não há agentes externos ativos |
