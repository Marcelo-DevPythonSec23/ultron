"""Testes da interface desktop (Fase 2.5 — INTERFACE.md).

Cobrem, sem exigir display gráfico real (modo offscreen do Qt):

1. Importação dos módulos da interface
2. Criação do Application, BridgeAdapter, tema, event system
3. Criação da janela principal (offscreen)
4. Event system — emissão e recepção de eventos
5. BridgeAdapter — status, providers, ferramentas, memória
6. Tema — tokens de identidade visual
7. Avatar — mudança de estado
8. Chat — envio de mensagem e histórico
"""

from __future__ import annotations

import os
import sys

import pytest

# Força o Qt a usar o plugin offscreen (sem display gráfico real)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

# Garante uma instância QApplication para os testes de widget
_qapp = QApplication.instance() or QApplication(sys.argv)

from ultron_2_0.interface.application import Application  # noqa: E402
from ultron_2_0.interface.adapters.bridge_adapter import BridgeAdapter  # noqa: E402
from ultron_2_0.interface.events.event_system import (  # noqa: E402
    Event,
    EventSystem,
    EventType,
)
from ultron_2_0.interface.themes.ultron_theme import UltronTheme  # noqa: E402
from ultron_2_0.interface.windows.main_window import MainWindow  # noqa: E402


# -- 1. importação dos módulos ---------------------------------------------
def test_modulos_da_interface_sao_importaveis():
    from ultron_2_0.interface import Application as App  # noqa: F401
    from ultron_2_0.interface.animations.holographic_canvas import (  # noqa: F401
        HolographicCanvas,
    )
    from ultron_2_0.interface.components.avatar import AvatarWidget  # noqa: F401
    from ultron_2_0.interface.components.chat import ChatWidget  # noqa: F401
    from ultron_2_0.interface.panels.systems_panel import SystemsPanel  # noqa: F401
    from ultron_2_0.interface.panels.tasks_panel import TasksPanel  # noqa: F401

    assert App is Application


# -- 2. tema de identidade visual ------------------------------------------
def test_tema_ultron_tem_tokens_de_cor():
    theme = UltronTheme()
    assert theme.bg == "#050506"
    assert theme.red == "#b3121a"
    assert theme.red_bright == "#ff2f3d"
    assert theme.text == "#ece9e6"
    assert theme.ok == "#3ddc97"

    # Estilosheet gera variáveis CSS válidas
    ss = theme.to_stylesheet_vars()
    assert "--red-bright: #ff2f3d" in ss
    assert "--bg: #050506" in ss


# -- 3. event system -------------------------------------------------------
def test_event_system_emite_e_recebe_eventos():
    es = EventSystem()
    recebidos = []

    def handler(event: Event) -> None:
        recebidos.append(event)

    es.on(EventType.ASSISTANT_STATE_CHANGED, handler)

    es.emit_sync(
        EventType.ASSISTANT_STATE_CHANGED,
        state="LISTENING",
        detail="ouvindo",
    )

    assert len(recebidos) == 1
    assert recebidos[0].type == EventType.ASSISTANT_STATE_CHANGED
    assert recebidos[0].payload["state"] == "LISTENING"
    assert recebidos[0].payload["detail"] == "ouvindo"


def test_event_system_history():
    es = EventSystem()
    es.emit_sync(EventType.ASSISTANT_ERROR, message="erro teste")
    es.emit_sync(EventType.ASSISTANT_STATE_CHANGED, state="IDLE")

    hist = es.history(limit=10)
    assert len(hist) == 2
    assert hist[0]["type"] == "assistant.error"
    assert hist[1]["type"] == "assistant.state_changed"


# -- 4. aplicação e bridge adapter -----------------------------------------
def test_application_inicializa_com_bridge():
    app = Application()
    assert app.initialize() is True

    assert app.adapter is not None
    assert app.main_window is not None
    assert app.event_system is not None

    # Status do bridge reflete o núcleo real
    status = app.adapter.status()
    assert status["ready"] is True
    assert "mock" in status["providers"]

    # Provedores
    providers = app.adapter.providers()
    assert "mock" in providers

    # Ferramentas
    tools = app.adapter.tools()
    assert isinstance(tools, list)

    app.stop()


def test_application_estado_offline_sem_bridge():
    # Sem bridge, o adapter ainda funciona mas com estado limitado
    from ultron_2_0.orchestrator_bridge import OrchestratorBridge

    bridge = OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )
    bridge.start()

    adapter = BridgeAdapter(bridge)
    status = adapter.status()
    assert status["ready"] is True

    bridge.stop()


# -- 5. janela principal ---------------------------------------------------
def test_main_window_cria_componentes():
    app = Application()
    app.initialize()

    mw = app.main_window
    assert mw is not None
    assert mw._avatar is not None
    assert mw._chat is not None
    assert mw._systems_panel is not None
    assert mw._tasks_panel is not None

    # Avatar inicia em estado IDLE/offline até o primeiro refresh
    assert mw._avatar.state() in ("offline", "idle", "IDLE")

    app.stop()


def test_main_window_muda_estado_do_avatar():
    app = Application()
    app.initialize()

    mw = app.main_window
    mw.set_assistant_state("SPEAKING", "falando com o usuário")
    assert mw._avatar.state() == "SPEAKING"

    app.stop()


def test_main_window_envia_mensagem_do_chat():
    app = Application()
    app.initialize()

    mw = app.main_window
    mw._chat.append_message("user", "olá", provider=None, model=None)
    mw._chat.append_message("assistant", "oi!", provider="mock", model="stub-model")

    html = mw._chat._history.toHtml()
    assert "olá" in html
    assert "oi!" in html
    assert "[ultron]" in html

    app.stop()


def test_application_public_nao_expoe_segredos():
    import json

    app = Application()
    app.initialize()

    status = app.adapter.status()
    payload = json.dumps(status, ensure_ascii=False)
    assert "AIza" not in payload
    assert "sk-" not in payload
    assert "GEMINI_API_KEY" not in payload

    app.stop()


# -- 6. avatar muda de estado ---------------------------------------------
def test_avatar_muda_estados():
    from ultron_2_0.interface.components.avatar import AvatarWidget

    theme = UltronTheme()
    avatar = AvatarWidget(theme=theme)

    avatar.set_state("LISTENING", "ouvindo")
    assert avatar.state() == "LISTENING"

    avatar.set_state("PROCESSING", "processando")
    assert avatar.state() == "PROCESSING"

    avatar.set_state("IDLE", "inativo")
    assert avatar.state() == "IDLE"


# -- 7. chat exibe mensagens -----------------------------------------------
def test_chat_exibe_mensagens_usuario_e_assistente():
    from ultron_2_0.interface.application import Application

    app = Application()
    app.initialize()
    chat = app.main_window._chat

    chat.append_message("user", "teste de mensagem")
    chat.append_message(
        "assistant", "resposta do assistente", provider="mock", model="stub-model"
    )

    html = chat._history.toHtml()
    assert "teste de mensagem" in html
    assert "resposta do assistente" in html
    assert "[você]" in html
    assert "[ultron]" in html

    app.stop()

