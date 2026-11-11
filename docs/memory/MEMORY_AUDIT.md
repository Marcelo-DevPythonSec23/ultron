# MEMORY_AUDIT — auditoria da memória existente

> **Data:** 2026-11-10
> **Método:** leitura do código real de `lain/`, `Mark-LVI-main/` e `ultron-2.0/`,
> execução da suíte e inspeção dos arquivos de dados. Documento descreve o que
> **existe**, não o que seria desejável.
> **Regra:** `lain/` e `Mark-LVI-main/` não foram modificados.

## 1. Resumo executivo

O ULTRON 2.0 **não tinha** um sistema de memória próprio antes desta etapa. O que
existia era:

1. o **histórico conversacional** do núcleo do lain, em SQLite;
2. um **armazenamento de fatos em JSON** reutilizado do Mark-LVI
   (`memory/memory_manager.py`), já ligado às tools `remember`/`recall`/`forget`
   na Etapa 4;
3. nenhuma distinção de tipo, escopo, versão, confiança, retenção ou expiração.

A implementação desta etapa **evolui** o item 2 em vez de criar um segundo
armazenamento: `MemoryEngine` mantém o `memory.json` como espelho canônico e
adiciona registros e histórico em arquivos laterais.

## 2. O que existia em cada projeto

### 2.1 `lain/` — núcleo ULTRON

| Item | Evidência | Conclusão |
|---|---|---|
| Histórico de conversas | `app/database/` (modelos/repositórios), `app/core/chat_service.py` | `IMPLEMENTED` — é histórico, **não** memória semântica |
| Contexto do turno | `app/core/context_manager.py`, `app/intelligence/prompt_engine.py` | `IMPLEMENTED` — janela de mensagens + personalidade |
| Memória de fatos | busca por `memory` em `lain/app` não encontrou módulo | **não existe** |
| Embeddings / busca vetorial | não há dependência nem código | **não existe** |
| Sessões | `conversation_id` por conversa no SQLite | `IMPLEMENTED` — usado como identidade de sessão |

O lain fornece a **autoridade** de contexto e histórico; ele não fornece memória
factual entre conversas.

### 2.2 `Mark-LVI-main/` — runtime operacional

| Item | Evidência | Conclusão |
|---|---|---|
| Armazenamento de fatos | `memory/memory_manager.py` | `IMPLEMENTED` (esquema antigo) |
| Esquema | `{"identity": {key: {"value", "updated"}}, ..., "sessions": [...]}` | categorias fixas; sem tipo/escopo/versão |
| Gravação | `remember()` → `update_memory()` → `save_memory()` | sobrescreve valor; não versiona |
| Busca | `search_memory()` lexical (`_score`) | `IMPLEMENTED`, sem semântica |
| Injeção no prompt | `format_memory_for_prompt()` (identidade + recentes + índice) | `IMPLEMENTED` no runtime original, **não usado** pelo 2.0 |
| Exclusão | `forget()` | `IMPLEMENTED`, sem autorização/auditoria |
| Sessões resumidas | `save_session_summary`, `pop_last_session` | `IMPLEMENTED` no runtime original, **não usado** pelo 2.0 |
| Limites | `MAX_VALUE_LENGTH=380`, `MEMORY_MAX_CHARS=200_000` | trunca valor; poda silenciosa acima do limite |
| Concorrência | `_lock` de I/O + `MEMORY_PATH` global de módulo | risco para múltiplas instâncias no mesmo processo |

O `memory_manager` **não** foi alterado. O 2.0 o importa e reposiciona
`MEMORY_PATH` para `ultron-2.0/data/memory.json` (nunca `long_term.json`).

### 2.3 `ultron-2.0/` — antes desta etapa

| Item | Evidência | Conclusão |
|---|---|---|
| `FactMemory` | `ultron_2_0/memory_tools.py` | `IMPLEMENTED` — fachada explícita sobre o manager |
| `remember`/`recall`/`forget` | mesmas tools via `ToolGateway` | `IMPLEMENTED` — só gravação explícita |
| `memory_type` | aceito pela tool e ignorado pelo armazenamento antigo | `PARTIAL` |
| Escopo/versão/expiração | não existiam | **não existe** |
| Injeção de memória no turno | não existia | **não existe** |
| Consolidação | não existia | **não existe** |

## 3. O que foi preservado, adaptado e criado

| Ação | Item | Justificativa |
|---|---|---|
| **Preservado** | `memory_manager.py` como armazenamento canônico subjacente | evita segundo armazenamento e mantém `remember`/`recall` e o painel funcionando |
| **Preservado** | histórico SQLite do lain | memória não substitui histórico |
| **Adaptado** | `FactMemory` (lock de caminho + reafirmação de `MEMORY_PATH`) | corrige corrida da global de módulo sem tocar no original |
| **Adaptado** | tools de memória passam a operar pelo `MemoryEngine` | mesma interface, semântica mais rica |
| **Criado** | `memory_engine.py` | tipos, escopo, versão, histórico, trust, retenção, consolidação |
| **Criado** | `memory_injection.py` | memória recuperada entra no prompt uma vez por turno |
| **Criado** | `memory_records.json` / `memory_history.json` | metadados e versões que o esquema antigo não expressa |
| **Não criado** | banco vetorial, embeddings, segundo DB | sem necessidade demonstrada; busca lexical já operava |

## 4. Duplicações e conflitos investigados

1. **Duas memórias concorrentes?** Não. `FactMemory` e `MemoryEngine` compartilham
   o mesmo arquivo canônico; o engine é a camada de metadados, não um segundo
   banco.
2. **Histórico divergente?** Não. O histórico de conversa continua exclusivamente
   no SQLite do lain. O `memory_history.json` guarda versões de **fatos**, não
   mensagens.
3. **Contexto misturado?** Resolvido por escopo explícito (`global`,
   `user:default`, `user:<outro>`, `session:<id>`) e escopos de leitura
   autorizados.
4. **`MEMORY_PATH` global?** Risco real. Mitigado por `_path_lock` (RLock) e por
   cada operação reafirmar `self.path` antes de tocar no manager.
5. **Poda silenciosa do manager antigo?** `_trim_to_limit()` só dispara perto de
   200 000 caracteres; o engine valida valores em 4 000 e mantém histórico. A
   poda antiga não é acionada no fluxo normal.

## 5. Lacunas (o que ainda não existe)

| Lacuna | Classificação | Motivo |
|---|---|---|
| Embeddings / similaridade semântica | `PLANNED` | nenhum provedor de embedding configurado; busca lexical + recência + confiança cobre o uso atual |
| Relações entre entidades (knowledge graph) | `PLANNED` | sem necessidade demonstrada |
| Captura automática de memória | **não desejada** | política explícita: só `remember` grava |
| Confirmação interativa de `forget` | `PARTIAL` | gateway recusa até existir UI de confirmação |
| Criptografia em repouso | `PLANNED` | arquivos JSON locais em texto; risco registrado |
| Backup/restauração automatizados | `PLANNED` | operação manual de cópia |
| Memória por agente | `PARTIAL` | escopo pode ser usado por agente, mas não há agentes externos ativos |
| Métricas de qualidade de recuperação | `PLANNED` | sem metodologia de avaliação implementada |

## 6. Fontes de verdade

1. **Código** (`memory_engine.py`, `memory_injection.py`, `memory_tools.py`) —
   fonte primária.
2. **Testes** (`tests/test_memory_engine.py`, `tests/test_memory_tools.py`) —
   comportamento validado.
3. **Este acervo** (`docs/memory/*`) — documentação derivada; em caso de
   divergência, o código e os testes prevalecem.

## 7. Evidência de integridade dos originais

- `lain/ultron.db`: 12 conversas / 48 mensagens, inalterado.
- `Mark-LVI-main/memory/long_term.json`: não é lido nem escrito pelo 2.0; o
  teste `test_memory_tools.py` verifica o mtime.
- `Mark-LVI-main/config/api_keys.json`: não criado nem editado.
- Nenhum arquivo de `lain/` ou `Mark-LVI-main/` alterado.
