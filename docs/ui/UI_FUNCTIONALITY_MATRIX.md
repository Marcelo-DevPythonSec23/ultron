# UI_FUNCTIONALITY_MATRIX — paridade funcional com a referência

**Fase:** 2.5
**Data:** 2026-11-11
**Regra:** só marcar `INTEGRADO` com código e teste/evidência. `N/A` e
`NÃO PORTADO` são decisões explícitas, não pendências escondidas.

Estados: `INTEGRADO`, `ADAPTADO`, `NÃO PORTADO`, `PLANNED`, `N/A`.

## 1. Monitoramento do sistema

| Recurso Mark-LVI | Estado no ULTRON | Evidência |
|---|---|---|
| CPU, RAM, temperatura, GPU, uptime, processos | `INTEGRADO` | `GET /api/system` → `marklvi_actions.system_snapshot()` (mesma função de `system_status`) |
| Barras com limiar de cor | `ADAPTADO` | medidores CSS com `aria-valuenow`; 65 %/85 % |
| NET (rede) | `NÃO PORTADO` | `get_system_status()` não expõe rede; não inventar métrica |

## 2. Conversa e histórico

| Recurso | Estado | Evidência |
|---|---|---|
| Chat por texto | `INTEGRADO` | `POST /api/chat` → `bridge.process_text` (mesmo orquestrador) |
| Histórico persistente | `INTEGRADO` | `GET /api/history` → `ChatService`; `test_web.py` |
| Nova conversa sem apagar histórico | `INTEGRADO` | `POST /api/new`; `test_new_encerra...` |
| Escolha de provider por turno | `INTEGRADO` | `provider` no corpo; `status.providers` |
| Streaming token a token | `NÃO PORTADO` | o HUD recebe a resposta final; streaming existe no núcleo, não na UI |
| Ferramentas usadas por turno | `INTEGRADO` | etiquetas de `tool_calls` em `/api/chat` e `/api/history` |

## 3. Autorização e segurança

| Recurso | Estado | Evidência |
|---|---|---|
| Confirmação de ação sensível | `INTEGRADO` | painel `/api/approvals` + `AuthorizationManager` (Fase 2) |
| Token de uso único, expiração, anti-replay | `INTEGRADO` | `test_authorization.py` (14), `test_web.py` |
| Aprovação por voz | `N/A` (recusa por design) | `_deny_sensitive_action` |

## 4. Atividade e auditoria

| Recurso | Estado | Evidência |
|---|---|---|
| Log de atividade | `ADAPTADO` | `ActivityLog` da sessão + `GET /api/activity` |
| Persistência do log em arquivo | `NÃO PORTADO` | decisão: não criar histórico paralelo; auditoria canônica é do núcleo |
| Classificação por tipo (turno/resposta/tool/erro/aprovação) | `INTEGRADO` | `web/activity.py`, `test_activity_*` |

## 5. Ferramentas e plugins

| Recurso | Estado | Evidência |
|---|---|---|
| Lista de ferramentas com contrato | `INTEGRADO` | `GET /api/tools` (contratos do Gateway) |
| Gerenciador de plugins | `NÃO PORTADO` | plugins fora do subset curado do 2.0 |
| Configuração por plugin | `NÃO PORTADO` | idem |
| Editor de ações/execução de shell | `N/A` | bloqueado por segurança |

## 6. Configurações

| Recurso | Estado | Evidência |
|---|---|---|
| Diagnóstico de núcleo/banco/memória/áudio | `INTEGRADO` | gaveta `#setup` ← `/api/status` |
| Seleção de dispositivo de áudio | `NÃO PORTADO` | voz é processo separado; HUD só informa os dispositivos |
| Nome do assistente / cor de destaque | `NÃO PORTADO` | identidade fixa por tokens (decisão de design) |
| Gravação de chaves (`api_keys.json`) | `N/A` | proibido; credenciais vêm do ambiente |
| Copiar comando de voz | `INTEGRADO` | `#copy-voice` |

## 7. Memória

| Recurso | Estado | Evidência |
|---|---|---|
| Navegar memória de longo prazo | `NÃO PORTADO` | memória é autoridade do núcleo; leitura via tool `recall` |
| Editar/excluir memória direto na UI | `N/A` | escrita só por tool + autorização (Fase 2) |
| Injeção de memória no prompt | `INTEGRADO` (núcleo) | `memory_injection.py`; não é componente da UI |

## 8. Conteúdo rico

| Recurso | Estado | Evidência |
|---|---|---|
| `show_content(title, text)` | `NÃO PORTADO` | sem tool correspondente no subset curado |
| `show_quiz` | `NÃO PORTADO` | idem |
| `show_review` | `NÃO PORTADO` | idem |
| `show_video` | `NÃO PORTADO` | idem |
| Avatar/viseme | `ADAPTADO` | canvas abstrato por estado real (sem rosto) |

## 9. Dashboard remoto

| Recurso | Estado | Evidência |
|---|---|---|
| Login remoto/dispositivo | `NÃO PORTADO` | superfície de ataque; HUD local |
| WebSocket de comandos | `NÃO PORTADO` | o HUD usa HTTP JSON; polling curto |
| Áudio do celular (PCM16) | `NÃO PORTADO` | voz local em processo separado |
| Upload/download de arquivos | `NÃO PORTADO` | segurança e escopo |
| HTTPS | `N/A` | bind local `127.0.0.1` |

## 10. Identidade visual e experiência

| Recurso | Estado | Evidência |
|---|---|---|
| Paleta centralizada | `INTEGRADO` | tokens `:root` |
| Animação holográfica | `ADAPTADO` | canvas por estado real; `prefers-reduced-motion` |
| Tema preto/vermelho do ULTRON | `INTEGRADO` | `--bg`…`--red-bright`; `test_hud_...tokens` |
| Responsividade | `INTEGRADO` | breakpoints 1200/780 |
| Acessibilidade por teclado | `INTEGRADO` | skip link, foco visível, `aria-*`; `test_hud_tem_acessibilidade...` |
| Sem CDN | `INTEGRADO` | `test_hud_serve_html...` |
| HUD abre microfone | `N/A` | declarado no rodapé; voz separada |

## 11. Resumo

- **INTEGRADO/ADAPTADO:** monitoramento, conversa/histórico, autorização,
  atividade, ferramentas, diagnóstico, identidade, responsividade,
  acessibilidade, animação.
- **NÃO PORTADO por decisão:** dashboard remoto, plugins, edição direta de
  memória, editor de credenciais, conteúdo rico (quiz/review/vídeo), streaming
  na UI, métrica de rede.
- **Nenhuma funcionalidade listada como pronta sem evidência de código/teste.**
