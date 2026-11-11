# SECURITY_AGENT — contexto do agente de segurança

## Responsabilidade
Garantir que a segurança viva no código: permissões, validação, confirmação,
timeouts, auditoria, proteção de credenciais e separação dado/instrução.

## Partes relevantes
`tool_gateway.py`, `tool_contracts.py`, `tool_loop.py`, `marklvi_actions.py`,
`bootstrap.py`, `web/app.py`; `Mark-LVI-main/core/confirm.py`,
`core/outcome.py`, `memory/config_manager.py`.

## Documentos obrigatórios
1. `docs/SECURITY.md`
2. `docs/TOOLS.md`
3. `docs/context/KNOWN_LIMITATIONS.md` §7
4. `docs/INTEGRATION_AUDIT.md` (riscos)
5. `docs/memory/MEMORY_SECURITY.md`

## Interfaces que deve respeitar
- Allowlist do gateway.
- Validação de schema/tipos/obrigatórios/desconhecidos.
- `requires_confirmation` para ações sensíveis.
- Timeout e tratamento de exceção.
- Nenhum shell/eval/exec genérico.
- Resultado externo marcado como dado não confiável.

## Restrições
- Nunca imprimir/logar `GEMINI_API_KEY` ou tokens.
- Nunca criar/editar `Mark-LVI-main/config/api_keys.json`.
- Nunca desativar validação para "fazer passar".
- HUD local: não expor à rede sem revisão.
- Cancelamento de thread não é cancelamento de execução: documentar.

## Testes que deve executar
`test_tool_gateway.py`, `test_faults.py`, `test_memory_tools.py` (recusa de
`forget`), `test_web.py` (contrato de entrada).

## Critérios de conclusão
- Nenhuma ferramenta executa fora do gateway.
- Segredos preservados.
- Riscos residuais documentados.
- Testes de falha e permissão passando.

## Coordenação
Com INTEGRATION (novas actions) e ARCHITECT (decisões de escopo). Nunca aprovar
sozinho a exposição de ação destrutiva.
