# MEMORY_TYPES — tipos, escopos e metadados

> **Fonte primária:** `ultron-2.0/ultron_2_0/memory_engine.py` (`MEMORY_TYPES`,
> `MemoryRecord`, `_normalize_type`, `_default_scope`).

## 1. Tipos de memória

| Tipo | Constante | Finalidade real no código | Escopo padrão | Retenção padrão | Estado |
|---|---|---|---|---|---|
| Trabalho | `working` | estado da tarefa/sessão atual | `session:default` | `working` (TTL 3600 s) | `IMPLEMENTED` (só via `store`) |
| Episódica | `episodic` | evento/experiência com data, atores e resultado | `global` | `permanent` | `IMPLEMENTED` (campos extras via API; tools não expõem) |
| Semântica | `semantic` | fato/conhecimento estruturado | `global` | `permanent` | `IMPLEMENTED` |
| Procedural | `procedural` | procedimento validado com etapas | `global` | `permanent` | `PARTIAL` (campos `steps`/`validated` existem; sem fluxo de validação) |
| Usuário | `user` | preferências/identidade do usuário | `user:default` | `permanent` | `IMPLEMENTED` |

Tipos duráveis (espelhados no `memory.json`): `episodic`, `semantic`,
`procedural`, `user`. `working` nunca é espelhado.

## 2. Campos de um registro (`MemoryRecord`)

| Campo | Tipo | Significado | Validação |
|---|---|---|---|
| `id` | `str` | identificador único (`uuid4().hex[:16]`) | gerado pelo engine |
| `key` | `str` | chave curta do fato | obrigatória, ≤ 120 chars |
| `value` | `str` | conteúdo | obrigatório, ≤ 4 000 chars, recusa credencial |
| `category` | `str` | categoria do esquema do Mark-LVI | `identity`, `preferences`, `projects`, `relationships`, `wishes`, `notes` |
| `memory_type` | `str` | um dos 5 tipos | enum `MEMORY_TYPES` |
| `scope` | `str` | isolamento | regex `^[a-z][a-z0-9_:-]{0,63}$` |
| `source` | `str` | origem (`tool:remember`, `legacy-memory.json`, …) | livre |
| `trust` | `str` | confiabilidade declarada | `confirmed`, `user_stated`, `inferred`, `untrusted` |
| `confidence` | `float` | confiança numérica | 0.0–1.0; derivada do trust |
| `tags` | `list[str]` | agrupamento por assunto | normalizadas, ordenadas, únicas |
| `retention` | `str` | política de retenção | `permanent`, `session`, `temporary`, `working` |
| `created_at`/`updated_at` | ISO-8601 UTC | linha do tempo | gerado |
| `version` | `int` | versão do registro | incrementa em `update` |
| `valid` | `bool` | validade lógica | expiração/invalidação |
| `supersedes` | `str \| None` | linhagem declarada | reservado para uso futuro |
| `expires_at` | ISO-8601 \| `None` | vencimento | memória de trabalho ganha TTL |
| `occurred_at` | ISO-8601 \| `None` | quando o episódio ocorreu | opcional |
| `actors`, `result` | `list[str]`, `str \| None` | atores e resultado do episódio | opcionais |
| `steps`, `validated` | `list[str]`, `bool` | etapas e validação do procedimento | opcionais |

## 3. Trust e confiança

| `trust` | `confidence` padrão | Uso esperado |
|---|---|---|
| `confirmed` | 1.0 | informação confirmada pelo usuário |
| `user_stated` | 0.9 | declarada pelo usuário (padrão de `remember`) |
| `inferred` | 0.6 | inferência — deve continuar identificada |
| `untrusted` | 0.2 | conteúdo externo; recebe penalidade no ranking |

O ranking usa `confidence` como bônus e aplica `-2` a `untrusted`
(`_score`). Uma memória não se torna instrução por estar armazenada: o bloco
injetado é marcado como **DADO** por `get_context`.

## 4. Escopos

| Escopo | Exemplo | Leitura padrão? | Escrita por tool? |
|---|---|---|---|
| `global` | `global` | sim | sim (`remember` sem escopo) |
| `user:default` | `user:default` | sim | sim (`memory_type=user`) |
| `user:<nome>` | `user:alice` | não | via API/engine |
| `session:<id>` | `session:s1` | não | via API/engine |
| `task:<id>` / `project:<id>` | reservado | não | via API/engine |

Isolamento é aplicado em `search`/`retrieve`/`get_context` por `read_scopes`.
Escopos de outros usuários/sessões ficam **apenas** no `memory_records.json`,
nunca no espelho global.

## 5. O que ainda não está exposto

- As tools `remember`/`recall`/`forget` expõem `memory_type`, mas **não** escopo,
  tags, trust, retenção, episódio ou procedimento. O `MemoryEngine` já suporta
  esses campos por API (ver [MEMORY_API.md](MEMORY_API.md)).
- A UI/HUD exibe memória via `FactMemory.entries()` (esquema antigo), não os
  metadados novos.
- `working` não é criada automaticamente pelo orquestrador; é usada por código
  que chame o engine com escopo de sessão autorizado.
