# UI_TESTING — testes e validação da interface

**Fase:** 2.5
**Data:** 2026-11-11
**Arquivo de testes:** `ultron-2.0/tests/test_web.py`

## 1. Como executar

```bash
cd ultron-2.0
./.venv/bin/python -m pytest tests/test_web.py -q    # foco em UI
./.venv/bin/python -m pytest -q                      # suíte completa
```

Os testes usam um `OrchestratorBridge` real com banco em memória
(`sqlite+aiosqlite:///:memory:`), `TestClient` do FastAPI e o
`ScriptedProvider` (implementa o contrato real `LLMProvider`). Não há mock de
unidade da conversa: o orquestrador, o gateway e a persistência são reais.

## 2. Cobertura de UI (21 testes em `test_web.py`)

| Teste | O que valida |
|---|---|
| `test_hud_serve_html_com_tokens_de_identidade` | HTML servido, title, tokens `--red-bright`, `fetch(`, ausência de CDN |
| `test_hud_tem_acessibilidade_e_movimento_reduzido` | `prefers-reduced-motion`, skip link, `aria-live`, `role=log`, `role=progressbar`, `aria-expanded`, canvas `aria-hidden`, `#core-state` |
| `test_hud_declara_que_nao_abre_microfone` | rodapé informa voz separada e que o HUD não abre microfone |
| `test_status_reflete_o_nucleo_real` | `/api/status` com provider, memória, banco, áudio inalterados |
| `test_status_sobrevive_a_falha_do_probe_de_audio` | falha de áudio vira `{error}`, sem derrubar o HUD |
| `test_status_expõe_busy_falso_quando_ocioso` | `status.busy` reflete ausência de turno |
| `test_tools_lista_o_subset_real_e_a_memoria` | `/api/tools` = contratos reais do Gateway |
| `test_system_usa_as_metricas_reais_do_host` | `/api/system` devolve o snapshot real (monkeypatch do snapshot) |
| `test_system_indisponivel_vira_503_sem_numeros_inventados` | falha do psutil → `503`, sem números falsos |
| `test_activity_registra_turno_e_resposta_do_nucleo` | `/api/activity` registra `turn` e `reply` reais do turno |
| `test_activity_limite_e_escopo_de_sessao` | `limit` respeitado; `scope=session` |
| `test_decisao_aprovada_registra_atividade_real` | aprovação entra no feed (regressão do `action_id`) |
| `test_chat_persiste_no_historico_do_nucleo` | `/api/chat` grava no histórico único |
| `test_chat_encadeia_a_mesma_conversa` | turnos caem na mesma conversa |
| `test_new_encerra_a_conversa_sem_apagar_o_historico` | `/api/new` mantém o histórico persistido |
| `test_falha_de_provedor_vira_502_controlado` | falha de provider → `502`, HUD continua |
| `test_mensagem_vazia_e_rejeitada_pelo_contrato` | validação Pydantic (`422`) |
| `test_hud_lista_aprova_e_libera_a_acao` | fluxo de autorização real pelo HUD |
| `test_hud_recusa_e_rejeita_replay_e_id_desconhecido` | `409`/`404` para replay/id inválido |
| `test_tool_calls_summary_tolera_metadata_invalido` | diagnóstico tolerante |
| `test_servidor_escuta_local_por_padrao` | bind `127.0.0.1:8765` |

## 3. Critérios do `INTERFACE.md` §9

| Critério | Cobertura |
|---|---|
| Navegação | skip link, gavetas com `aria-expanded`, `Escape`, links internos |
| Componentes | 21 testes exercitam rotas e marcadores; `UI_COMPONENTS.md` mapeia cada um |
| Configurações | gaveta de diagnóstico alimentada por `/api/status`; controles de movimento/compacto |
| Comunicação com backend | todos os endpoints testados com dados reais |
| Integração de voz | HUD **não** abre microfone; teste garante a declaração e a voz separada |
| Estados de carregamento | `busy`, mensagens `pending`, `—`/“indisponível” sem números falsos |
| Tratamento de erros | `502` de turno, `503` de sistema, `409`/`404` de autorização, banner |
| Persistência de configurações | não há configuração persistida na UI (decisão); estado vem do núcleo |
| Compatibilidade de funcionalidades | `UI_FUNCTIONALITY_MATRIX.md` com estado e evidência por item |
| Regressão da interface | `test_web.py` roda junto da suíte completa |

## 4. Resultados registrados

| Data | Suíte | Resultado |
|---|---|---|
| 2026-11-11 | `tests/test_web.py` (Fase 2.5) | **21 passed** |
| 2026-11-11 | ULTRON 2.0 completo | **136 passed** |
| 2026-11-11 | Regressão lain | **64 passed** |

## 5. Verificação visual

A interface foi verificada por renderização local do HTML e pelo smoke HTTP do
HUD (`/` 200, endpoints reais). A validação visual fina (contraste, proporção,
animação em navegador real) é manual e deve ser repetida ao alterar tokens ou
layout; os testes automatizados garantem estrutura, acessibilidade e dados, não
estética.

## 6. Limitações

- Não há teste automatizado de interação real de navegador (sem Playwright no
  ambiente); a lógica JS é coberta por revisão e pelos contratos que ela consome.
- `prefers-reduced-motion` é testado pela presença da regra/atributo, não por
  medição de quadros.
- Streaming e conteúdo rico (quiz/review/vídeo) não fazem parte da UI atual.
