"""Janela principal da interface desktop ULTRON 2.0 (INTERFACE.md).

Layout de 3 colunas:
- Esquerda: painel Systems (métricas reais)
- Centro: Avatar + Chat
- Direita: Atividade + Tasks + Autorizações

Gavetas:
- Controles (provider, movimento reduzido, compacto, nova conversa, refresh)
- Configurações (diagnóstico somente leitura)
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..adapters.bridge_adapter import BridgeAdapter
from ..animations.holographic_canvas import AssistantState
from ..components.avatar import AvatarWidget
from ..components.chat import ChatWidget
from ..panels.systems_panel import SystemsPanel
from ..panels.tasks_panel import TasksPanel
from ..themes.ultron_theme import UltronTheme


class ControlsDrawer(QFrame):
    """Gaveta de controles (INTERFACE.md §12)."""

    def __init__(self, adapter: BridgeAdapter, theme: UltronTheme, parent=None) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._theme = theme
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("controls-drawer")
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("controles")
        title.setStyleSheet(
            "color: #ff2f3d; font-size: 14px; font-weight: bold; font-family: mono; text-transform: uppercase;"
        )
        layout.addWidget(title)

        # Provider
        from PySide6.QtWidgets import QComboBox

        self._provider_combo = QComboBox()
        self._provider_combo.addItem("padrão")
        self._provider_combo.setStyleSheet(
            f"""
            QComboBox {{
                background: {self._theme.bg_2};
                color: {self._theme.text};
                border: 1px solid {self._theme.line};
                border-radius: {self._theme.radius_sm};
                font-family: {self._theme.mono};
                font-size: 12px;
                padding: 6px 10px;
            }}
            """
        )
        layout.addWidget(QLabel("provedor:"))
        layout.addWidget(self._provider_combo)

        # Reduzir movimento
        from PySide6.QtWidgets import QCheckBox

        self._reduce_motion = QCheckBox("reduzir movimento")
        self._reduce_motion.setStyleSheet(
            f"color: {self._theme.text}; font-family: {self._theme.mono}; font-size: 12px;"
        )
        layout.addWidget(self._reduce_motion)

        # Layout compacto
        self._compact = QCheckBox("layout compacto")
        self._compact.setStyleSheet(
            f"color: {self._theme.text}; font-family: {self._theme.mono}; font-size: 12px;"
        )
        layout.addWidget(self._compact)

        layout.addSpacing(12)

        # Botões
        from PySide6.QtWidgets import QPushButton

        self._new_btn = QPushButton("nova conversa")
        self._new_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {self._theme.panel_solid};
                color: {self._theme.text};
                border: 1px solid {self._theme.line};
                border-radius: {self._theme.radius_sm};
                font-family: {self._theme.mono};
                font-size: 12px;
                padding: 8px 16px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{
                border: 1px solid {self._theme.red_bright};
            }}
            """
        )
        layout.addWidget(self._new_btn)

        self._refresh_btn = QPushButton("atualizar status")
        self._refresh_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {self._theme.panel_solid};
                color: {self._theme.text};
                border: 1px solid {self._theme.line};
                border-radius: {self._theme.radius_sm};
                font-family: {self._theme.mono};
                font-size: 12px;
                padding: 8px 16px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{
                border: 1px solid {self._theme.red_bright};
            }}
            """
        )
        layout.addWidget(self._refresh_btn)

        layout.addStretch()


class SettingsDrawer(QFrame):
    """Gaveta de configurações - diagnóstico somente leitura (INTERFACE.md §12)."""

    def __init__(self, adapter: BridgeAdapter, theme: UltronTheme, parent=None) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._theme = theme
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("settings-drawer")
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("configurações")
        title.setStyleSheet(
            "color: #ff2f3d; font-size: 14px; font-weight: bold; font-family: mono; text-transform: uppercase;"
        )
        layout.addWidget(title)

        self._info_label = QLabel("carregando diagnóstico...")
        self._info_label.setObjectName("settings-info")
        self._info_label.setStyleSheet(
            f"color: {self._theme.muted}; font-family: {self._theme.mono}; font-size: 12px; line-height: 1.5;"
        )
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)
        layout.addStretch()

        self.refresh()

    def refresh(self) -> None:
        try:
            status = self._adapter.status()
            lines = []
            lines.append(f"núcleo: {'online' if status.get('ready') else 'offline'}")
            lines.append(f"provedor padrão: {status.get('default_provider', '—')}")
            lines.append(f"providers: {', '.join(status.get('providers', [])) or '—'}")
            lines.append(f"banco: {status.get('database', '—')}")
            lines.append(f"memória: {status.get('memory', '—')}")
            lines.append(f"ferramentas: {', '.join(status.get('tools', [])) or '—'}")
            lines.append(f"aprovações pendentes: {status.get('pending_approvals', 0)}")

            # Roteador (Fase 3)
            router = status.get("router")
            if router:
                lines.append("")
                lines.append("roteador:")
                lines.append(f"  habilitado: {router.get('enabled', False)}")
                lines.append(f"  fallback: {router.get('config', {}).get('fallback_enabled', False)}")

            # Agentes (Fase 4)
            agents = status.get("agents")
            if agents:
                lines.append("")
                lines.append(f"agentes: {agents.get('total', 0)}")
                lines.append(f"  tipos: {', '.join(agents.get('types', [])) or '—'}")

            # Integrações (Fase 5)
            integrations = status.get("integrations")
            if integrations:
                lines.append("")
                lines.append("integrações:")
                for target, info in integrations.get("integrations", {}).items():
                    lines.append(f"  {target}: {'habilitado' if info.get('enabled') else 'desabilitado'}")

            self._info_label.setText("\n".join(lines))
        except Exception as exc:  # noqa: BLE001
            self._info_label.setText(f"erro ao carregar diagnóstico: {exc}")


class MainWindow(QMainWindow):
    """Janela principal da interface desktop ULTRON 2.0.

    Não cria um segundo cérebro: consome os serviços existentes através
    do BridgeAdapter e apresenta estados e resultados reais.
    """

    def __init__(self, adapter: BridgeAdapter, theme: UltronTheme | None = None) -> None:
        super().__init__()
        self._adapter = adapter
        self._theme = theme or UltronTheme()
        self._set_window_title()
        self._setup_ui()
        self._start_status_refresh()

    def _set_window_title(self) -> None:
        self.setWindowTitle("ULTRON 2.0 — interface desktop")

    def _setup_ui(self) -> None:
        # Widget central com splitter de 3 colunas
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        # Coluna esquerda: Systems
        self._systems_panel = SystemsPanel(
            adapter=self._adapter, theme=self._theme, parent=self
        )
        splitter.addWidget(self._systems_panel)

        # Coluna centro: Avatar + Chat
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self._avatar = AvatarWidget(theme=self._theme, parent=self)
        self._avatar.setFixedSize(300, 340)
        center_layout.addWidget(self._avatar, alignment=Qt.AlignCenter)

        self._chat = ChatWidget(
            adapter=self._adapter, theme=self._theme, parent=self
        )
        center_layout.addWidget(self._chat, stretch=1)

        splitter.addWidget(center)

        # Coluna direita: Tasks
        self._tasks_panel = TasksPanel(
            adapter=self._adapter, theme=self._theme, parent=self
        )
        splitter.addWidget(self._tasks_panel)

        # Proporções: 1 : 2 : 1
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 1)

        main_layout.addWidget(splitter)

        # Barra de status inferior
        self._status_bar = self.statusBar()
        self._status_bar.setStyleSheet(
            f"""
            QStatusBar {{
                background: {self._theme.panel_solid};
                color: {self._theme.muted};
                font-family: {self._theme.mono};
                font-size: 11px;
                border-top: 1px solid {self._theme.line};
            }}
            """
        )
        self._status_bar.showMessage("inicializando...")

        # Aplica tema
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background: {self._theme.bg};
            }}
            QWidget {{
                background: {self._theme.bg};
                color: {self._theme.text};
            }}
            QFrame#controls-drawer, QFrame#settings-drawer {{
                background: {self._theme.bg_2};
                border: 1px solid {self._theme.line};
                border-radius: {self._theme.radius};
            }}
            """
        )

    def _start_status_refresh(self) -> None:
        """Atualiza o status periodicamente."""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_status)
        self._refresh_timer.start(2000)
        self._refresh_status()

    def _refresh_status(self) -> None:
        try:
            status = self._adapter.status()
            ready = status.get("ready", False)
            providers = status.get("providers", [])
            tools = status.get("tools", [])

            self._status_bar.showMessage(
                f"núcleo: {'online' if ready else 'offline'}  |  "
                f"provedores: {', '.join(providers) or '—'}  |  "
                f"ferramentas: {len(tools)}"
            )

            # Atualiza avatar com base no estado
            if ready:
                self._avatar.set_state(AssistantState.IDLE, "operacional")
            else:
                self._avatar.set_state(AssistantState.OFFLINE, "offline")

            # Atualiza gaveta de configurações se existir
            if hasattr(self, "_settings_drawer"):
                self._settings_drawer.refresh()

        except Exception:  # noqa: BLE001
            self._status_bar.showMessage("erro ao obter status")

    # -- ações de interface -------------------------------------------------
    def set_assistant_state(self, state: str, detail: str | None = None) -> None:
        """Atualiza o estado visual do assistente (recebido via event system)."""
        self._avatar.set_state(state, detail)

    def append_chat_message(
        self, role: str, content: str, provider: str | None = None, model: str | None = None
    ) -> None:
        self._chat.append_message(role, content, provider=provider, model=model)

    def show_chat_error(self, message: str) -> None:
        self._chat.show_error(message)

    def show_tool_result(self, tool_name: str, result: str) -> None:
        self._chat.show_tool_result(tool_name, result)


__all__ = ["MainWindow", "ControlsDrawer", "SettingsDrawer"]
