# MEMORY_LIFECYCLE — criação, versionamento, retenção e exclusão

> **Fonte primária:** `ultron-2.0/ultron_2_0/memory_engine.py`
> (`store`, `update`, `delete`, `expire`, `consolidate`, `_ensure_loaded`).

## 1. Ciclo de vida

```text
                    store(key, value, …)
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
     valor idêntico no mesmo     valor novo / diferente
     escopo+categoria+chave              │
              │                         ▼
        deduplicado (sem         cria registro v1
        escrita)                        │
                                        ├── espelha em memory.json (se canônico)
                                        └── registra "created" no histórico

     update(id, changes) ──► versão +1 ──► "updated" + previous/current (se valor)
     expire()/busca       ──► valid=False (sem apagar)
     delete(id, authorized) ──► remove registro + espelho + versões + tombstone
```

## 2. Criação e deduplicação (`store`)

1. valida chave/valor (obrigatórios, limites, recusa de credenciais);
2. normaliza tipo, escopo, trust, retenção e tags;
3. procura registro **válido** no mesmo `(scope, category, key)`;
4. se o valor normalizado é idêntico → devolve o registro com
   `deduplicated: true` (nenhuma escrita);
5. se o valor difere → delega a `update` (não sobrescreve cegamente);
6. se não existe → cria `MemoryRecord` v1, salva, espelha (se escopo canônico) e
   registra `created`.

`working` sem `expires_at` recebe TTL de 3 600 s (`_WORKING_TTL_SECONDS`).

## 3. Atualização versionada (`update`)

Campos permitidos: `value`, `tags`, `trust`, `retention`, `expires_at`,
`confidence`, `source`, `valid`. Campos fora disso → `ValueError`.

- `version += 1`, `updated_at` renovado;
- valor novo é revalidado (inclusive contra credenciais);
- `previous`/`current` vão ao histórico **somente** quando o valor muda;
- `memory.json` é reescrito com o valor atual quando o escopo é canônico;
- `valid=False` invalida sem apagar (sai da recuperação, mantém histórico).

## 4. Expiração e retenção

| Retenção | Efeito |
|---|---|
| `permanent` | não expira por tempo |
| `session` | registro de sessão; expiração explícita quando definida |
| `temporary` | expiração explícita quando definida |
| `working` | TTL padrão de 3 600 s |

`expire()` e `search()` marcam `valid=False` para registros vencidos; **não há
expurgo silencioso**. A decisão de apagar continua sendo `delete` autorizado.
Recência entra no ranking, mas não apaga nada.

## 5. Exclusão (`delete`)

Exige `authorized=True` (`PermissionError` caso contrário). Ao autorizar:

1. remove o registro de `memory_records.json`;
2. remove o valor do `memory.json` quando o escopo é canônico;
3. apaga **todas** as entradas de histórico daquele `record_id`;
4. grava tombstone `{"op": "deleted", "content": "[redacted: deleted]"}`;
5. registra auditoria.

A exclusão só é reportada como concluída depois de remover as versões antigas —
não se declara algo excluído enquanto cópias continuam legíveis no histórico.

`forget(key, category)` resolve o id (escopo `global`) e chama `delete`
autorizado; pela interface, o gateway recusa antes disso por falta de confirmação
(ver [MEMORY_SECURITY.md](MEMORY_SECURITY.md)).

## 6. Consolidação (`consolidate`)

Somente leitura. Percorre registros válidos (de um escopo ou de todos) e relata:

- **duplicatas:** mesmo valor normalizado em registros diferentes;
- **conflitos:** mesma `(scope, key)` com valores divergentes;
- **relações:** tags que conectam mais de um registro;
- **sugestões:** texto para avaliação humana.

Nunca reescreve, nunca apaga, nunca escolhe um valor. Informações inferidas
continuam identificadas pelo `trust`.

## 7. Adoção de fatos legados

Fatos do `memory.json` sem registro ganham metadados na primeira carga. A adoção
não modifica o arquivo canônico e não duplica em execuções seguintes. Detalhes em
[MEMORY_STORAGE.md](MEMORY_STORAGE.md) §4.

## 8. Histórico

- operações registradas: `created`, `updated`, `deleted`;
- teto de 2 000 entradas, descartando as mais antigas;
- `history(record_id)` filtra por registro;
- conteúdo anterior só é guardado em mudança de valor;
- exclusão substitui o histórico do registro por um tombstone sem conteúdo.

## 9. Limitações

- Não há resumo/compactação automática de episódios (consolidação só relata).
- `supersedes` existe no modelo, mas nenhum fluxo o preenche ainda.
- Não há migração de esquema versionada além do campo `version` dos arquivos.
- Retenção `session`/`temporary` não têm varreduras agendadas; expiram quando
  consultadas ou quando `expire()` é chamado.
- Conflitos não são resolvidos automaticamente — por decisão explícita.
