# MEMORIA — Evolução da Memória do ULTRON 2.1 (Fase 6)

> **Status:** IMPLEMENTADO (Fase 6 concluída). Ver `docs/context/TECHNICAL_DECISIONS.md`
> (ADR-017), `tests/test_memory_phase6.py` (16 testes) e
> `docs/roadmap/ULTRON_21_PHASE6_REPORT.md`.

## 1. Objetivo

Expandir a capacidade de recuperação e relacionamento de informações da
memória do ULTRON, preservando o `MemoryEngine` existente, a compatibilidade
com tipos/escopos existentes e a regra de que embeddings/criptografia/backup
não são dependências obrigatórias (AGENTS.md §4.6).

## 2. Arquitetura — extensões opcionais (sem quebrar o existente)

O `MemoryEngine` (`memory_engine.py`) foi preservado integralmente. A Fase 6
adiciona três módulos novos e métodos no engine, sem alterar contratos
existentes:

```
ultron_2_0/
├── memory_engine.py        # preservado: store/update/delete/search/retrieve/
│                           # get_context/consolidate/expire/stats/remember/
│                           # recall/forget + métodos Fase 6 abaixo
├── memory_semantic.py      # NOVO: SemanticIndex (busca semântica opcional)
├── memory_backup.py        # NOVO: backup_memory / restore_memory (ZIP)
└── memory_encryption.py    # NOVO: MemoryEncryption (criptografia opcional)
```

Novos métodos no `MemoryEngine`:

| Método | Responsabilidade |
|---|---|
| `search_semantic(query, top_k, scopes)` | Busca semântica opcional; devolve `[]` sem embeddings |
| `retrieve_hybrid(query, limit, budget_chars, semantic_weight)` | Recuperação híbrida (léxica + semântica) |
| `backup(dest_zip)` | Backup dos 3 arquivos canônicos em ZIP (não destrutivo) |
| `restore(source_zip, confirm)` | Restauração (requer `confirm=True`) |
| `encryption_status()` | Status da criptografia (sem expor chave) |
| `encrypt_memory_file(file_path)` | Criptografa arquivo de memória (opcional) |
| `decrypt_memory_file(file_path, dest_path)` | Descriptografa (opcional) |

## 3. Busca semântica OPCIONAL (`memory_semantic.py`)

O `SemanticIndex` tenta importar `sentence-transformers`. Se não instalado,
`available=False` e todas as operações devolvem resultados vazios sem levantar
exceção — a memória cai de volta para a busca léxica do `MemoryEngine.search`
(recuperação lexical preservada).

- Não é adicionada a `requirements.txt` (dependência opcional).
- A chave de busca é `f"{chave} {valor}"` de cada registro.
- Similaridade por cosseno sobre embeddings normalizados.

## 4. Recuperação híbrida (`retrieve_hybrid`)

Mescla busca léxica (`search`, sempre executada) com semântica (quando
disponível), unificando por `id` com pontuação combinada ponderada por
`semantic_weight`. Sem embeddings, resulta equivalente à busca léxica.

Possui orçamento de caracteres (`budget_chars`) para controlar o contexto
enviado ao modelo.

## 5. Backup e restauração (`memory_backup.py`)

- `backup_memory(source_dir, dest_zip)` — ZIP com `manifest.json` +
  `memory.json`, `memory_records.json`, `memory_history.json`. Manifesto
  contém apenas contagens e caminhos (não expor conteúdo dos fatos).
- `restore_memory(source_zip, dest_dir, confirm=True)` — sobrescreve os três
  arquivos canônicos; requer `confirm=True` (evita restauração acidental).
- Não destrutivo: backup só lê.

## 6. Criptografia opcional em repouso (`memory_encryption.py`)

- `MemoryEncryption` usa `cryptography.fernet` se instalado; senão, desativa.
- Chave via `ULTRON2_MEMORY_ENCRYPTION_KEY` (base64) ou arquivo `memory.key`.
- A chave NUNCA é impressa, logada ou duplicada.
- `generate_key_file()` gera um novo arquivo de chave (sem recriar se existir).

## 7. Critérios de Fase 6 atendidos

| Critério | Status |
|---|---|
| Recuperação semântica testada | ✅ `search_semantic`/`retrieve_hybrid` com fallback para léxico |
| Recuperação lexical preservada | ✅ `MemoryEngine.search` inalterado, 17 testes verdes |
| Backup e restauração validados | ✅ round-trip testado (`test_memory_phase6.py`) |
| Criptografia testada | ✅ opcional, testada quando `cryptography` disponível |
| Compatibilidade com memória existente | ✅ `memory_engine.py` preservado, todos os testes existentes verdes |

## 8. Limitações conhecidas

- Nenhum servidor/provedor de embeddings configurado; `sentence-transformers`
  não instalado por padrão → busca semântica desativa, fallback léxico.
- `cryptography` não instalado por padrão → criptografia desativa.
- Backup/restauração operam sobre arquivos do 2.0 (`data/`); não tocam
  `lain/ultron.db` nem `Mark-LVI-main/memory/long_term.json`.
- Restauração sobrescreve arquivos (requer confirmação explícita).

## 9. Próximas etapas

- Fase 7 — Autonomia operacional (`Planner`, `TaskDecomposer`,
  `WorkflowEngine`, `Scheduler`, `RecoveryManager`, `StateTracker`).
- Fase 8 — Validação e estabilização (`docs/roadmap/ULTRON_21_FINAL_REPORT.md`).
