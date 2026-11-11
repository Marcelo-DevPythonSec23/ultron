# BACKEND_AGENT — contexto do agente de núcleo/backend

## Responsabilidade
Manter o núcleo do lain funcionando dentro do 2.0: `core_runtime`, providers,
contexto, persistência e ciclo de vida.

## Partes relevantes
`ultron_2_0/core_runtime.py`, `bootstrap.py`, `orchestrator_bridge.py`,
`tool_loop.py`; `lain/app/core/*`, `lain/app/intelligence/*`,
`lain/app/database/*`, `lain/app/config.py`.

## Documentos obrigatórios
1. `PROJECT_CONTEXT.md`
2. `docs/ARCHITECTURE.md`
3. `docs/context/MODULE_MAP.md`
4. `docs/context/DEPENDENCY_MAP.md`
5. `docs/TESTING.md`

## Interfaces que deve respeitar
- `Settings` do lain (`.env` absoluto, `DATABASE_URL` isolado).
- `ProviderRegistry` (não acoplar a um SDK).
- `Orchestrator.process_chat` (não reimplementar).
- `run_coro`/`chat_sync` para acesso cross-loop.

## Restrições
- Nunca abrir `lain/ultron.db`.
- Não criar segundo banco/histórico.
- Não usar `except Exception: pass` para esconder falhas.
- Não alterar `LLMRequest`/`ChatRequest` do lain sem decisão.

## Testes que deve executar
`test_bootstrap.py`, `test_core_runtime.py`, `test_bridge.py`,
`test_faults.py`; regressão do lain (64).

## Critérios de conclusão
- Inicialização e encerramento controlados.
- Banco isolado confirmado.
- Providers registrados e testados.
- Sem regressão no lain.

## Coordenação
Com ARCHITECT, INTEGRATION e QA. Qualquer mudança de contrato do provider deve
ser combinada com o agente de integração.
