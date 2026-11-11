# MEMORY_API — contratos reais do Motor de Memória

> **Fonte primária:** `ultron-2.0/ultron_2_0/memory_engine.py`,
> `ultron_2_0/memory_tools.py`, `ultron_2_0/memory_injection.py`,
> `ultron_2_0/core_runtime.py`.
>
> A interface conceitual do `MEMORY.md` era assíncrona. A implementação é
> **síncrona** porque todo o armazenamento é I/O local de arquivo pequeno:
> executores de ferramenta já rodam em worker threads e a injeção usa
> `asyncio.to_thread`. Não há métodos vazios: cada operação valida, persiste e
> devolve um resultado real.

## 1. `MemoryEngine`

### Construção

```python
MemoryEngine(
    path: str | Path | None = None,          # padrão: ultron-2.0/data/memory.json
    *,
    records_path: str | Path | None = None,  # padrão: memory_records.json ao lado
    history_path: str | Path | None = None,  # padrão: memory_history.json ao lado
    read_scopes=("global", "user:default"),
    working_ttl_seconds=3600,
)
```

Atributos: `facts` (`FactMemory`), `path`, `records_path`, `history_path`,
`read_scopes`, `working_ttl_seconds`.

### `store`

```python
store(
    key, value, *,
    category="notes",
    memory_type=None,       # working|episodic|semantic|procedural|user
    scope=None,
    source="ultron-2.0",
    trust="user_stated",    # confirmed|user_stated|inferred|untrusted
    tags=None,
    retention=None,         # permanent|session|temporary|working
    expires_at=None,
    occurred_at=None,
    actors=None,
    result=None,
    steps=None,
    validated=False,
) -> dict
```

Retorna o `MemoryRecord` como dicionário + `stored: true` + `deduplicated: bool`.
Pode delegar a `update` quando o valor muda.

Levanta `ValueError` para key/valor inválidos, credencial, tipo/escopo/trust
inválidos.

### `update`

```python
update(memory_id, changes: dict, *, reason="") -> dict
# campos: value, tags, trust, retention, expires_at, confidence, source, valid
```

Levanta `ValueError` para campo não permitido, `KeyError` se o id não existe.

### `delete`

```python
delete(memory_id, *, authorized=False, reason="") -> dict
```

`PermissionError` sem `authorized=True`. Retorna
`{"removed": bool, "id", "key", "category", "scope", "message"}`.

### `search`

```python
search(query="", *, filters=None, scopes=None, limit=20) -> list[RetrievedMemory]
# filters: memory_type, category, tags, trust, require_valid
```

Cada `RetrievedMemory` tem `record`, `score` e `matched`; `as_dict()` inclui
`score` e `matched`.

### `retrieve`

```python
retrieve(query="", *, scopes=None, limit=8, budget_chars=None) -> list[RetrievedMemory]
```

### `get_context`

```python
get_context(query="", *, scopes=None, budget_chars=1200, limit=12) -> str
```

Devolve o bloco pronto para o `system_instruction` ou `""`.

### Contratos de compatibilidade com as tools

```python
remember(key, value, category="notes", memory_type=None) -> dict
recall(query="", limit=8) -> str
forget(key, category="notes") -> dict
```

`remember` usa `source="tool:remember"`/`trust="user_stated"`; `recall` é leitura;
`forget` procura `(category, key)` nos escopos de leitura (`global` +
`user:default`) e chama `delete(authorized=True)`. O gateway só o executa após
autorização de uso único da interface (CLI/HUD).

### Ciclo de vida e observabilidade

```python
consolidate(scope=None) -> dict   # somente leitura
expire() -> int                   # invalida vencidos
entries() -> list[dict]           # painel/UI, mais recente primeiro
history(record_id=None) -> list[dict]
stats() -> dict                   # contadores, caminhos, distribuição
```

## 2. Tools registradas no gateway

| Tool | Obrigatórios | Opcionais | Permissões | Confirmação | Timeout |
|---|---|---|---|---|---|
| `remember` | `key`, `value` | `category`, `memory_type` | `memory:write` | não | 5 s |
| `recall` | — | `query`, `limit` | `memory:read` | não | 5 s |
| `forget` | `key` | `category` | `memory:write`, `memory:delete` | **sim** | 5 s |

`register_memory_tools(gateway, memory_engine)` aceita `FactMemory` ou
`MemoryEngine` (contrato mínimo `remember/recall/forget`).

`memory_type` aceito pela tool: `semantic`, `user`, `episodic`, `procedural`.
`working` não é exposto à tool (é escopo de sessão, não fato durável).

## 3. Injeção no provedor

```python
MemoryInjectionProvider(
    inner,                    # LLMProvider real
    engine,                   # MemoryEngine
    *,
    scopes=None,              # padrão: engine.read_scopes
    budget_chars=1200,
    limit=12,
)
```

Delega `provider_id`, `default_model`, `health_check`, `generate_response`,
`generate_stream`, `generate_response_streaming`; expõe `engine`, `scopes`,
`budget_chars` e delega atributos desconhecidos ao interno.

## 4. Wiring no núcleo

`UltronCoreRuntime(..., memory_path=None, memory_budget_chars=1200)`:

- cria `MemoryEngine` **sempre** (mesmo com `enable_tools=False`);
- `runtime.memory_engine` é o motor; `runtime.memory` é `engine.facts`
  (compatibilidade com a Etapa 4);
- `_wrap(provider)` = `MemoryInjectionProvider(ToolCallingProvider(provider), engine)`;
- `register_provider(provider)` aplica o mesmo empilhamento.

```python
from ultron_2_0.core_runtime import UltronCoreRuntime

runtime = UltronCoreRuntime(default_provider="mock")
runtime.start_background()
runtime.memory_engine.store("linguagem_preferida", "Python",
                            category="preferences", memory_type="user")
resposta = runtime.chat_sync("qual linguagem eu prefiro?")
runtime.stop_background()
```

## 5. Erros

| Situação | Exceção / resultado |
|---|---|
| key/valor vazio ou grande | `ValueError` |
| conteúdo parece credencial | `ValueError` |
| tipo/escopo/trust/retenção inválidos | `ValueError` |
| update de campo não permitido | `ValueError` |
| id inexistente em `update` | `KeyError` |
| delete sem autorização | `PermissionError` |
| id inexistente em `delete` | `{"removed": False, ...}` |
| memória indisponível na injeção | turno segue sem memória (logado) |
| arquivo corrompido | `_read_json` devolve `None`; engine opera vazio |

## 6. O que a API não faz

- Não executa ferramentas nem chama modelos.
- Não cria histórico de conversa.
- Não armazena credenciais.
- Não resolve conflitos automaticamente.
- Não faz backup.
