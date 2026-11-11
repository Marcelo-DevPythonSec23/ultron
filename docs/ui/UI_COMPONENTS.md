# UI_COMPONENTS — componentes do HUD ULTRON 2.0

**Fase:** 2.5
**Data:** 2026-11-11
**Arquivo:** `ultron-2.0/ultron_2_0/web/static/index.html` (HTML/CSS/JS locais,
sem CDN). Este documento mapeia cada componente ao dado real que o alimenta.

## 1. Cabeçalho (`<header>`)

| Elemento | ID | Dado real |
|---|---|---|
| Indicador de saúde | `#health` | `status.ready`, `status.busy`, estado de erro |
| Marca | `.brand` | texto fixo `ULTRON 2.0` |
| Pílula de estado | `#pill` / `#pill-text` | conectando · operacional · processando · erro |
| Provider padrão | `#provider-default` | `status.default_provider` |
| Uptime do HUD | `#uptime` | `status.web_uptime_seconds` |
| Relógio | `#clock` | hora local do navegador (`toLocaleTimeString`) |
| Botão Controles | `#open-controls` | abre a gaveta `#controls` |
| Botão Configurações | `#open-setup` | abre a gaveta `#setup` |

Ambos os botões expõem `aria-expanded` e `aria-controls`; `Escape` fecha.

## 2. Núcleo holográfico

| Elemento | Dado real |
|---|---|
| `<canvas id="core">` | desenho abstrato; cor/velocidade por `state.ready`, `state.busy`, `state.error` |
| `#core-state` (`role="status"`, `aria-live`) | "inicializando" · "operacional" · "processando" · "erro" |
| `#core-detail` | detalhe textual do estado atual |

O canvas é `aria-hidden="true"`; toda informação existe em texto. Sem
`prefers-reduced-motion`, anima; com, desenha um quadro estático.

## 3. Painel Sistema

| Medidor | ID | Fonte |
|---|---|---|
| CPU | `#m-cpu` / `#v-cpu` / `#f-cpu` | `metrics.cpu_percent` |
| RAM | `#m-ram` / `#v-ram` / `#f-ram` | `metrics.ram_percent` |
| TEMP | `#m-temp` / `#v-temp` / `#f-temp` | `metrics.cpu_temp_c` |
| GPU | `#m-gpu` / `#v-gpu` / `#f-gpu` | `metrics.gpu_percent` |
| Uptime | `#sys-uptime` | `metrics.uptime` |
| Processos | `#sys-procs` | `metrics.process_count` |
| Amostra | `#sys-sampled` | `sampled_at` |
| Erro | `#sys-error` | `503` de `/api/system` |

Cada medidor é `role="progressbar"` com `aria-valuenow`/`aria-valuetext`;
valores ausentes (ex.: GPU inexistente) aparecem como "—" e "indisponível".
Cores de alerta só mudam por limiar real (65 % atenção, 85 % crítico).

## 4. Conversa

| Elemento | Dado real |
|---|---|
| `#messages` (`role="log"`, `aria-live="polite"`) | `/api/history` (mensagens persistidas pelo núcleo) |
| `#conversation-id` | `status.conversation_id` (8 primeiros caracteres) ou "nova" |
| `#composer` / `#input` | envia `POST /api/chat` |
| `#provider-select` | `status.providers`; opção "padrão" = `null` |
| `#new` | `POST /api/new` (histórico anterior preservado) |

Cada mensagem do assistente mostra provider · modelo e etiquetas de ferramentas
(`tool_calls` com `ok`/falha). Enquanto o turno roda, a mensagem do usuário fica
`pending` e o composer é desabilitado.

## 5. Autorizações pendentes (`#approvals-panel`)

| Elemento | Dado real |
|---|---|
| Painel | oculto quando não há pendências |
| Contador | `#approvals-count` |
| Cartão | ferramenta + argumentos exatos em JSON |
| Expiração | `seconds_remaining` (atualizado a cada poll de 1 s sem recriar DOM) |
| Ações | `Autorizar` → `POST .../approve`; `Recusar` → `.../reject` |

O token nunca aparece no DOM. Replay/expiração/id desconhecido viram erro
controlado (`409`/`404`) exibido no banner.

## 6. Atividade (`#activity`)

Feed de eventos da **sessão** (`GET /api/activity`, escopo `session`):
`turn`, `reply`, `tool`, `error`, `approval`, `conversation`. Não é histórico
paralelo: reiniciar o processo limpa o feed; a conversa continua no SQLite do
núcleo. Cada item mostra horário, tipo e texto.

## 7. Ferramentas (`#tools`)

Lista os contratos reais de `GET /api/tools`: nome, assinatura, descrição,
etiquetas de confirmação, timeout e permissões. Sem gateway, mostra lista vazia
("nenhuma ferramenta registrada").

## 8. Gaveta Controles (`#controls`)

| Controle | Efeito real |
|---|---|
| `#ctrl-provider` | espelha o provider do próximo turno |
| `#reduce-motion` | desliga animação CSS/canvas |
| `#compact` | reduz altura do núcleo e da conversa |
| `#ctrl-new` | nova conversa |
| `#ctrl-refresh` | recarrega status, sistema, ferramentas, atividade e aprovações |

## 9. Gaveta Configurações (`#setup`)

Diagnóstico somente leitura: núcleo, provider, providers, banco, memória,
microfone, alto-falante, agentes (declarado "não implementados — Fase 4"),
comando de voz e lista de ferramentas. `Copiar comando` copia
`python -m ultron_2_0.voice` (com fallback de seleção).

## 10. Rodapé (`<footer>`)

Declara que a interface é local, que o núcleo é a autoridade única e que a voz
roda em processo separado. Não há estado simulado.

## 11. Tokens de identidade (`:root`)

`--bg`, `--bg-2`, `--panel`, `--panel-solid`, `--graphite`, `--line`,
`--line-strong`, `--red-deep`, `--red`, `--red-bright`, `--red-glow`, `--text`,
`--muted`, `--faint`, `--ok`, `--warn`, `--err`, `--radius`, `--radius-sm`,
`--mono`, `--sans`. Trocar a identidade é trocar tokens, não dezenas de regras.
