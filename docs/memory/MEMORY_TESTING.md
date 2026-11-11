# MEMORY_TESTING — testes, evidências e limitações

> **Fonte primária:** `ultron-2.0/tests/test_memory_engine.py` (17 testes) e
> `ultron-2.0/tests/test_memory_tools.py` (8 testes).

## 1. Como executar

```bash
cd ultron-2.0
./.venv/bin/python -m pytest tests/test_memory_engine.py -q   # 17
./.venv/bin/python -m pytest tests/test_memory_tools.py -q   # 8
./.venv/bin/python -m pytest -q                               # suíte completa
```

Os testes do motor **não são mocks do armazenamento**: usam `tmp_path`, leem e
escrevem arquivos JSON reais e reabrem o engine para validar persistência. O
único dublê é o provedor scriptável (`tests/fakes.py::ScriptedProvider`), que
implementa o contrato real `LLMProvider` e registra a requisição recebida.

## 2. Cobertura por teste (`test_memory_engine.py`)

| # | Teste | O que valida |
|---|---|---|
| 1 | `test_persistencia_entre_instancias` | sobrevive a reabertura; cria `memory.json` e `memory_records.json` |
| 2 | `test_adocao_de_fatos_legados_do_memory_json` | fato do esquema antigo ganha registro, sem duplicar |
| 3 | `test_diferenciacao_dos_tipos_de_memoria` | 5 tipos; `working` exige escopo de sessão e nasce com TTL |
| 4 | `test_recuperacao_textual_ranqueia_o_relevante` | ranking lexical; palavra sem match não retorna tudo |
| 5 | `test_recuperacao_por_categoria_e_tag` | filtros por tag e categoria |
| 6 | `test_isolamento_de_escopo` | `user:alice` ≠ `user:bob`; escopo não autorizado é invisível |
| 7 | `test_atualizacao_versiona_e_preserva_historico` | versão +1, `previous`/`current`, espelho atualizado |
| 8 | `test_deduplicacao_de_valor_identico` | segundo store idêntico não cria registro |
| 9 | `test_exclusao_exige_autorizacao_e_remove_rastros` | `PermissionError`; exclusão limpa valor/histórico; tombstone sem conteúdo |
| 10 | `test_consolidacao_relata_sem_alterar_memoria` | duplicatas/conflitos/relações sem reescrever |
| 11 | `test_orcamento_de_contexto` | bloco cabe no orçamento; cabeçalho "DATA, not instructions" |
| 12 | `test_working_memory_expira_sem_apagar_em_silencio` | expirado vira `valid=False`, registro permanece |
| 13 | `test_seguranca_recusa_credenciais_e_escopos_invalidos` | recusa segredo, escopo e tipo inválidos |
| 14 | `test_injecao_de_memoria_no_prompt` | memória entra no `system_instruction` preservando identidade |
| 15 | `test_memoria_sem_resultado_nao_altera_o_prompt` | sem memória, prompt intacto |
| 16 | `test_runtime_injeta_memoria_no_turno` | wiring real do runtime injeta no turno; caminho isolado |
| 17 | `test_ferramentas_de_memoria_operam_pelo_motor` | `remember`/`recall` pelo gateway; `forget` recusado sem confirmação |

## 3. Mapa com `MEMORY.md` §16

| Requisito do prompt | Cobertura | Estado |
|---|---|---|
| 1. Persistência | teste 1 | ✅ |
| 2. Recuperação textual | testes 4, 5 | ✅ |
| 3. Recuperação semântica | — | ❌ `PLANNED` (não há embeddings) |
| 4. Isolamento de usuários | teste 6 | ✅ (escopo lógico; sem autenticação) |
| 5. Isolamento de sessões | testes 3, 6, 12 | ✅ |
| 6. Memória episódica | teste 3 | ✅ (tipo); campos extras só por API |
| 7. Memória semântica | testes 1, 4 | ✅ |
| 8. Memória procedural | teste 3 | ✅ (tipo/campos); sem fluxo de validação |
| 9. Atualização | teste 7 | ✅ |
| 10. Exclusão | teste 9 | ✅ |
| 11. Deduplicação | teste 8 | ✅ |
| 12. Consolidação | teste 10 | ✅ (somente leitura) |
| 13. Conflitos | teste 10 | ✅ (detecta, não resolve) |
| 14. Expiração | testes 3, 12 | ✅ |
| 15. Falhas de armazenamento | — | ⚠️ `PARTIAL`: leitura corrompida é tolerada; sem teste dedicado a `OSError` na escrita |
| 16. Falhas de embeddings | — | n/a: não há embeddings |
| 17. Controle de permissões | testes 9, 13, 17 | ✅ |
| 18. Integração com o Core | testes 14, 15, 16 | ✅ |
| 19. Integração com agentes | teste 6 | ⚠️ `PARTIAL`: escopo suportado; agentes externos não existem |
| 20. Limites de contexto | teste 11 | ✅ |

## 4. Testes de memória já existentes (`test_memory_tools.py`, 8)

Cobrem o contrato da Etapa 4: `remember`/`recall`/`forget`, categorias, recusa de
`forget` pelo gateway, nada gravado automaticamente e
`Mark-LVI-main/memory/long_term.json` intocado. Eles continuam passando com o
`MemoryEngine` no gateway.

## 5. Resultados da suíte

| Data | Suíte | Resultado |
|---|---|---|
| 2026-11-10 | `test_memory_engine.py` | **17 passed** |
| 2026-11-10 | ULTRON 2.0 completa | **109 passed** |
| 2026-11-10 | Regressão lain | **64 passed** |

Ver `docs/TESTING.md` para o consolidado.

## 6. Limitações dos testes

- Não há chamada real a Gemini; a injeção é validada com provedor scriptável.
- Não há teste de dois processos concorrentes no mesmo arquivo.
- Não há teste de corrupção/escrita parcial induzida (só leitura tolerante).
- Não há teste de embeddings (não implementados).
- Não há avaliação de qualidade de recuperação (precisão/recall).
- A aprovação de `forget` é testada por handler/threads e HTTP, sem TTY ou navegador reais.

Nenhuma dessas lacunas é apresentada como funcionalidade concluída.
