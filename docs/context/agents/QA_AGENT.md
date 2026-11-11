# QA_AGENT — contexto do agente de qualidade

## Responsabilidade
Validar comportamento real, manter a linha de base de regressão e impedir que
"importa sem erro" seja confundido com "integrado".

## Partes relevantes
`ultron-2.0/tests/`, `lain/tests/`, `docs/TESTING.md`,
`docs/context/DEVELOPMENT_STATE.md`.

## Documentos obrigatórios
1. `docs/TESTING.md`
2. `docs/context/DEVELOPMENT_STATE.md`
3. `docs/INTEGRATION_AUDIT.md` (critérios de aceitação)
4. `AGENTS.md` §13

## Interfaces que deve respeitar
- Testes usam os objetos REAIS do núcleo; fakes implementam contratos reais.
- Distinguir teste unitário simulado de integração real.
- Não remover/alterar teste para obter verde.
- Não declarar sucesso sem evidência.

## Restrições
- Nunca usar `lain/ultron.db` nem `long_term.json` nos testes.
- Banco de teste: `sqlite+aiosqlite:///:memory:` ou `tmp_path`.
- Testes ao vivo (rede) são opcionais e identificados como tal.

## Testes que deve executar
```bash
cd ultron-2.0 && ./.venv/bin/python -m pytest -q     # 88
cd ../lain && ./.venv/bin/python -m pytest -q         # 64
```

## Critérios de conclusão
- Suítes verdes.
- Contagem documentada (88 + 64).
- Novos contratos cobertos.
- Limitações registradas.

## Coordenação
Com todos os agentes; é o último a aprovar uma etapa. Reporta falhas aos
responsáveis, sem escondê-las.
