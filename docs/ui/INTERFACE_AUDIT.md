# INTERFACE_AUDIT — auditoria da interface de referência (Mark-LVI)

**Fase:** 2.5 (`INTERFACE.md`)
**Data:** 2026-11-11
**Escopo:** auditoria integral da interface do Mark-LVI para reconstruir a
**funcionalidade** no HUD web do ULTRON 2.0, sem portar o runtime PyQt6.
**Origem somente leitura:** `Mark-LVI-main/` (não modificado).

## 1. Inventário de arquivos

| Arquivo | Linhas | Papel real |
|---|---:|---|
| `ui.py` | 7 504 | Aplicação PyQt6: janela, paleta, canvas holográfico, painéis, overlays |
| `dashboard/server.py` | 1 312 | Servidor HTTPS/FastAPI do dashboard remoto (login, WS, upload, áudio do celular) |
| `dashboard/static/app.html` | 596 | Dashboard remoto (HTML/CSS/JS, WebSocket, microfone PCM16) |
| `dashboard/static/login.html` | 224 | Login do dashboard remoto |

Não há build, bundler nem dependência de CDN no dashboard: HTML/CSS/JS são
servidos localmente.

## 2. Estrutura da janela PyQt6 (`ui.py`)

Constantes reais (linhas 85–91):

- `APP_VERSION = "MARK LVI"`, `APP_PROTOCOL` derivado.
- Janela padrão `980×700`; mínimo `820×580`.
- Painel esquerdo fixo `148 px`; painel direito fixo `340 px`.

Composição (métodos de `MainWindow`, a partir da linha 4397):

1. **Header** (`_build_header`, ~5390) — versão, botão de gaveta, nome do
   assistente, relógio, botões de controle.
2. **Painel esquerdo** (`_build_left_panel`, ~5477) — `SYS MONITOR` com barras
   CPU/MEM/NET/GPU/TMP (`MetricBar`, linha 943), bloco de IP/host, status.
3. **Centro** — `HudCanvas` (linha 405) com avatar/viseme e `_paint_core`
   (linha 697), além de área de conteúdo (`show_content`), quiz (`show_quiz`),
   review (`show_review`) e vídeo (`show_video`).
4. **Painel direito** (`_build_right_panel`, ~5550) — log de atividade
   (`LogWidget`, linha 1004) e controles.
5. **Footer** (~6437) — estado/protocolo e atalhos.
6. **Composer** — entrada de texto e controles de voz.

### 2.1 Paleta e identidade

`class C` (linha 96) centraliza as cores (`BG`, `DARK`, `PANEL`, `PANEL2`,
`BORDER`, `BORDER_B`, `PRI`, `PRI_DIM`, `PRI_GHO`, `ACC`, `ACC2`, `GREEN`,
`TEXT`, `TEXT_MED`, `TEXT_DIM`). Fontes em `QFont("Courier New", tamanho)`.
`apply_ui_accent()` permite trocar a cor de destaque salva na configuração.

### 2.2 Animação holográfica

`HudCanvas` desenha, por frame:

- grade de pontos em camada cacheada (`_make_grid`);
- anéis concêntricos com dash e rotação;
- núcleo pulsante (`_paint_core`) com gradiente radial;
- marcas radiais;
- `glance(dx, dy)` para reação a gesto;
- `push_visemes(frames, hop, at)` e `set_audio_level(level)` para falar;
- `_on_screen()` evita animar fora de tela (economia).

O estado visual reage a: ocioso, ouvindo, processando, falando, erro.

## 3. Overlays e painéis (funcionalidades reais)

| Classe | Linha | Função |
|---|---:|---|
| `SetupOverlay` | 1444 | Configuração inicial (chave de API, provedor, voz) |
| `CustomizeOverlay` | 1667 | Nome do assistente, cor de destaque, preferências |
| `PluginManagerOverlay` | 1885 | Lista/habilita plugins |
| `_HudOverlay` | 1996 | Base de overlays |
| `ConfirmBanner` | 2018 | Confirmação de ação sensível |
| `AudioDeviceOverlay` | 2098 | Seleção de microfone/alto-falante |
| `MemoryOverlay` | 2458 | Navegação da memória de longo prazo |
| `ProvidersOverlay` | 2681 | Provedores/modelos e chaves |
| `ClipboardPanel` | 3792 | Histórico de área de transferência |
| `PluginSettingsOverlay` | 3878 | Configuração por plugin |
| `RemoteKeyOverlay` | 4134 | Chave de acesso remoto (dashboard) |

## 4. Dashboard remoto (`dashboard/`)

Rotas reais em `dashboard/server.py`:

- `GET /login`, `POST /login`, `GET /auto-login`
- `POST /api/device-login`, `POST /api/revoke-devices`
- `POST /api/command`, `POST /api/wake`
- `WebSocket /ws`, `WebSocket /ws/phone-audio`
- `POST /api/upload` (duas variantes), `GET /api/files`,
  `GET /uploads/{filename}`

`app.html` usa WebSocket para comandos e envia áudio do celular em PCM16.
`login.html` autentica o acesso remoto.

## 5. Dependências e restrições observadas

- **PyQt6** é a base de `ui.py`: exige stack gráfica pesada, inadequada ao
  ambiente de ~4 GB de RAM sem GPU (ADR-013).
- O dashboard remoto expõe HTTPS, login por dispositivo, upload de arquivos e
  captura de microfone do celular: superfície de ataque que não deve ser
  reaberta sem requisito e autorização explícitos.
- `SetupOverlay`/`ProvidersOverlay` gravam chaves via
  `memory/config_manager.py` em `config/api_keys.json` — arquivo que o ULTRON
  2.0 **não pode criar nem editar**.

## 6. O que foi reaproveitado como funcionalidade

| Recurso da referência | Destino no ULTRON |
|---|---|
| Métricas CPU/RAM/temp/GPU/uptime | `GET /api/system` → `marklvi_actions.system_snapshot()` (mesma função da tool `system_status`) |
| Painel de conversa | HUD central + `POST /api/chat` pelo mesmo `process_text` |
| Log de atividade | `ActivityLog` (ring buffer da sessão) + `GET /api/activity` |
| Confirmação de ação sensível | painel de autorizações do HUD + `AuthorizationManager` (Fase 2) |
| Lista de ferramentas | `GET /api/tools` a partir dos contratos reais do `ToolGateway` |
| Estado de provedores/áudio | `GET /api/status` (núcleo real) |
| Canvas holográfico | canvas abstrato por estado real (ocioso/processando/erro) |
| Cores centralizadas | tokens CSS (`--red`, `--red-bright`, …) |

## 7. O que **não** foi portado (e por quê)

| Recurso | Motivo |
|---|---|
| Widgets PyQt6, avatar/viseme, rosto | stack pesada; identidade ULTRON é abstrata por decisão |
| Dashboard remoto (login/WS/upload/áudio do celular) | segurança e escopo; HUD é local (`127.0.0.1`) |
| `SetupOverlay`/`ProvidersOverlay` gravando chaves | proibido tocar `config/api_keys.json`; credenciais vêm do ambiente |
| `CustomizeOverlay` (cor/nome) | identidade fixa por tokens; sem editor de configuração de UI |
| `PluginManager`/`PluginSettings` | plugins não fazem parte do subset curado do 2.0 |
| `MemoryOverlay` (edição direta) | memória é autoridade do núcleo; escrita só por tool/autorização |
| `ClipboardPanel`, `RemoteKeyOverlay` | sem requisito no 2.0 |
| `show_quiz`/`show_review`/`show_video` | dependem de tools que não estão no subset curado |

A matriz completa, com estado por funcionalidade, está em
`UI_FUNCTIONALITY_MATRIX.md`.
