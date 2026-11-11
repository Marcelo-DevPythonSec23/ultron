# INTEGRATION_AGENT — contexto do agente de integração

## Responsabilidade
Integrar capacidades do Mark-LVI ao núcleo por adaptadores e contratos, sem
transformar o Mark-LVI em segundo orquestrador.

## Partes relevantes
`ultron_2_0/marklvi_actions.py`, `tool_contracts.py`, `tool_gateway.py`,
`memory_tools.py`; `Mark-LVI-main/actions/*`,
`Mark-LVI-main/core/action_loader.py`, `core/outcome.py`, `core/confirm.py`.

## Documentos obrigatórios
1. `docs/INTEGRATION_MAP.md`
2. `docs/INTEGRATION_AUDIT.md`
3. `docs/TOOLS.md`
4. `docs/SECURITY.md`
5. `docs/context/MODULE_MAP.md`

## Interfaces que deve respeitar
- `ToolContract` (schema, permissões, timeout, confirmação, fonte).
- `ToolGateway.execute` — nunca chamar action diretamente do orquestrador.
- Resultado de action é **dado não confiável**.
- Memória: `memory_tools.FactMemory`, nunca outro `long_term.json`.

## Restrições
- Não executar `Mark-LVI-main/main.py` nem o loop Gemini Live original.
- Não importar `core/stt.py`/`core/tts.py` (código morto).
- Não conectar actions com `shell=True`, `pyautogui` sem failsafe ou leitura de
  `api_keys.json` sem revisão de segurança.
- Não criar `Mark-LVI-main/config/api_keys.json`.

## Testes que deve executar
`test_integration_tools.py`, `test_tool_gateway.py`, `test_tool_loop.py`,
`test_memory_tools.py`, `test_faults.py`.

## Critérios de conclusão
- Ferramenta registrada com contrato real e testada.
- Nenhuma execução fora do gateway.
- Documentada em `docs/TOOLS.md` e `INTEGRATION_MAP.md`.
- Sem alteração nos originais.

## Coordenação
Com BACKEND (provider/loop) e SECURITY (permissões). Toda nova action passa por
revisão de segurança antes de entrar no subset.
