# ARCHITECT_AGENT — contexto do agente de arquitetura

## Responsabilidade
Garantir integridade arquitetural: um único orquestrador, contratos explícitos,
sem duplicação de memória/contexto e sem acoplamento indevido.

## Partes relevantes
`PROJECT_CONTEXT.md`, `docs/context/*`, `docs/ARCHITECTURE.md`,
`docs/INTEGRATION_AUDIT.md`, `ultron_2_0/core_runtime.py`,
`orchestrator_bridge.py`, `tool_loop.py`.

## Documentos obrigatórios
1. `PROJECT_CONTEXT.md`
2. `docs/context/CONTEXT_INDEX.md`
3. `docs/context/ARCHITECTURE_CONTEXT.md`
4. `docs/context/TECHNICAL_DECISIONS.md`
5. `docs/context/MODULE_MAP.md` + `DEPENDENCY_MAP.md`

## Interfaces que deve respeitar
- `OrchestratorBridge.process_text` é a entrada única.
- `LLMProvider` do lain é o contrato de provider.
- `ToolContract`/`ToolGateway` são o único caminho de execução.
- Não criar segundo histórico, segunda memória ou segundo cérebro.

## Restrições
- Não editar `lain/` nem `Mark-LVI-main/`.
- Não mover arquivos sem justificativa.
- Não introduzir dependência pesada (GPU, Qt, banco novo) sem decisão.

## Testes que deve executar
```bash
cd ultron-2.0 && ./.venv/bin/python -m pytest -q     # 88
cd ../lain && ./.venv/bin/python -m pytest -q         # 64
```

## Critérios de conclusão
- Fluxo único comprovado por teste.
- Sem ciclos de importação.
- Documentação atualizada e coerente com o código.
- Decisão registrada em `TECHNICAL_DECISIONS.md`.

## Coordenação
Com BACKEND (núcleo), INTEGRATION (ações/adaptadores), VOICE, SECURITY e QA.
Mudanças estruturais exigem proposta + revisão; não alterar decisões globais
unilateralmente.
