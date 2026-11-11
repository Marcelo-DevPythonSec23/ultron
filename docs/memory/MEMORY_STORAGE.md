# MEMORY_STORAGE — armazenamento e integridade

> **Fonte primária:** `ultron-2.0/ultron_2_0/memory_engine.py`,
> `ultron_2_0/memory_tools.py`, `Mark-LVI-main/memory/memory_manager.py`
> (reutilizado sem modificação).

## 1. Decisão de armazenamento

Não foi criado um novo banco. A menor solução capaz de atender aos requisitos foi
**três arquivos JSON locais** irmãos, com escrita atômica:

- o armazenamento canônico **já existente** do Mark-LVI (`memory.json`);
- um sidecar de metadados (`memory_records.json`);
- um sidecar de histórico (`memory_history.json`).

Isso preserva `remember`/`recall`/painel, evita migração destrutiva e mantém a
operação funcional sem embeddings, sem rede e sem SQL adicional.

## 2. Arquivos

### 2.1 `memory.json` — espelho canônico

Esquema real do `memory_manager`:

```json
{
  "identity": { "cidade": { "value": "Curitiba", "updated": "2026-11-10" } },
  "preferences": {},
  "projects": {},
  "relationships": {},
  "wishes": {},
  "notes": {},
  "sessions": []
}
```

- Contém apenas memórias **duráveis** de escopo `global` ou `user:default`.
- É escrito via `FactMemory.remember/forget` → `memory_manager`.
- Memórias `working`, `user:<outro>` e `session:*` **não** aparecem aqui.
- O `memory_manager` trunca valores em 380 caracteres (`MAX_VALUE_LENGTH`) neste
  arquivo; o registro completo em `memory_records.json` mantém até 4 000.

### 2.2 `memory_records.json` — registro completo

```json
{
  "version": 1,
  "records": [
    {
      "id": "b1f2…",
      "key": "cidade",
      "value": "Curitiba",
      "category": "identity",
      "memory_type": "user",
      "scope": "user:default",
      "source": "tool:remember",
      "trust": "user_stated",
      "confidence": 0.9,
      "tags": [],
      "retention": "permanent",
      "created_at": "2026-11-10T12:00:00+00:00",
      "updated_at": "2026-11-10T12:00:00+00:00",
      "version": 1,
      "valid": true,
      "expires_at": null
    }
  ]
}
```

É a fonte de **metadados, tipos, escopos e validade**. `search`/`retrieve` leem
daqui. Também aceita o formato legado de lista pura (compatibilidade de leitura).

### 2.3 `memory_history.json` — versões e tombstone

```json
{
  "version": 1,
  "entries": [
    {
      "record_id": "b1f2…",
      "op": "updated",
      "at": "2026-11-10T12:05:00+00:00",
      "version": 2,
      "source": "tool:remember",
      "reason": "store com valor diferente…",
      "previous": "São Paulo",
      "current": "Curitiba"
    }
  ]
}
```

- Um `previous`/`current` só é gravado quando o **valor** muda; mudanças de
  tags/confiança não duplicam conteúdo.
- Ao excluir, todas as entradas daquele `record_id` são removidas e fica um
  tombstone `{"op": "deleted", "content": "[redacted: deleted]"}`.
- Teto de 2 000 entradas (`_MAX_HISTORY_ENTRIES`); as mais antigas são
  descartadas.

## 3. Integridade

| Mecanismo | Implementação | Efeito |
|---|---|---|
| Escrita atômica | `_atomic_write`: tmp + `os.replace` | leitor nunca vê JSON parcial |
| Lock do engine | `threading.RLock` | serializa store/update/delete/consolidação |
| Lock de caminho | `memory_tools._path_lock` + `FactMemory._use()` | corrige a global `MEMORY_PATH` do manager |
| Leitura tolerante | `_read_json` registra erro e devolve `None` | arquivo corrompido não derruba o núcleo |
| Registro inválido | `MemoryRecord.from_dict` ignora campos desconhecidos | evolução de esquema sem perda total |
| Teto de valor | 4 000 caracteres | evita payload descontrolado |
| Teto de histórico | 2 000 entradas | evita crescimento infinito |

## 4. Adoção de fatos legados

Na primeira operação após a atualização, `_ensure_loaded` percorre
`FactMemory.entries()` e cria um `MemoryRecord` para cada fato que ainda não tem
registro:

- `source = "legacy-memory.json"`;
- `memory_type = "user"` para `identity`/`preferences`, senão `semantic`;
- `scope = "global"`, `trust = "user_stated"`, `version = 1`;
- `created_at` derivado de `updated` quando possível.

A adoção **não altera o `memory.json`**: apenas cria os metadados que tornam o
fato atualizável/excluível por id. Teste:
`test_memory_engine.py::test_adocao_de_fatos_legados_do_memory_json`.

## 5. Isolamento de dados

| Dado | Local | Observação |
|---|---|---|
| Histórico de conversas | `ultron-2.0/data/ultron2.db` | SQLite do núcleo |
| Fatos canônicos | `ultron-2.0/data/memory.json` | escopos canônicos |
| Metadados de memória | `ultron-2.0/data/memory_records.json` | todos os escopos |
| Versões | `ultron-2.0/data/memory_history.json` | sem conteúdo após exclusão |
| Banco real do lain | `lain/ultron.db` | **nunca tocado** |
| Memória original do Mark-LVI | `Mark-LVI-main/memory/long_term.json` | **nunca lido/escrito** |

## 6. Limitações de armazenamento

- **Sem criptografia em repouso:** os JSON são texto simples no disco local.
  Risco registrado; proteção é de perímetro (diretório do usuário).
- **Sem backup automático:** cópia manual do diretório `data/`.
- **Sem índice invertido/DB:** a busca varre todos os registros em memória; para o
  volume doméstico é suficiente, mas não escala para milhões.
- **Espelho canônico mais estreito:** o `memory.json` não guarda tipo/escopo; quem
  precisa do registro completo deve consultar o engine, não o arquivo.
- **`MEMORY_PATH` é global** no módulo original; o lock resolve a corrida dentro
  do processo, mas dois **processos** escrevendo no mesmo arquivo não são
  coordenados (fora do escopo atual).
