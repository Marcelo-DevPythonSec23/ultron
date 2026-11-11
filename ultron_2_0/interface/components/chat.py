"""Componente de chat e communications (INTERFACE.md §9).

Campo de entrada, envio de mensagens, histórico de conversas, exibição de
respostas, diferenciação visual entre usuário e assistente, indicador de
processamento, exibição de erros, suporte a respostas faladas.

Toda mensagem utiliza o fluxo central do ULTRON (OrchestratorBridge).
Não cria conversa independente.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..adapters.bridge_adapter import BridgeAdapter
from ..themes.ultron_theme import UltronTheme


class ChatWidget(QWidget):
    """Widget de chat integrado ao núcleo ULTRON."""

    # Sinais para notificar a janela principal
    message_sent = Signal(str)
    tool_called = Signal(str, str)  # tool_name, result
    error_occurred = Signal(str)

    def __init__(
        self,
        adapter: BridgeAdapter,
        theme: UltronTheme | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._theme = theme or UltronTheme()
        self._conversation_id: Optional[str] = None
        self._processing = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("chat-widget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Histórico de conversa
        self._history = QTextEdit()
        self._history.setObjectName("chat-history")
        self._history.setReadOnly(True)
        self._history.setMinimumHeight(300)
        self._history.setStyleSheet(
            f"""
            QTextEdit {{
                background: {self._theme.bg_2};
                color: {self._theme.text};
                border: 1px solid {self._theme.line};
                border-radius: {self._theme.radius_sm};
                font-family: {self._theme.sans};
                font-size: 13px;
                padding: 12px;
                selection-background-color: {self._theme.red_bright};
            }}
            """
        )
        layout.addWidget(self._history)

        # Indicador de processamento
        self._status_label = QLabel("pronto")
        self._status_label.setObjectName("chat-status")
        self._status_label.setAlignment(Qt.AlignRight)
        self._status_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self._theme.muted};
                font-family: {self._theme.mono};
                font-size: 11px;
                margin-right: 8px;
            }}
            """
        )
        layout.addWidget(self._status_label)

        # Linha de entrada
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setObjectName("chat-input")
        self._input.setPlaceholderText("Digite sua mensagem para o ULTRON...")
        self._input.setStyleSheet(
            f"""
            QLineEdit {{
                background: {self._theme.bg_2};
                color: {self._theme.text};
                border: 1px solid {self._theme.line};
                border-radius: {self._theme.radius_sm};
                font-family: {self._theme.mono};
                font-size: 13px;
                padding: 10px 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self._theme.red_bright};
            }}
            QLineEdit:disabled {{
                color: {self._theme.faint};
                border: 1px solid {self._theme.graphite};
            }}
            """
        )
        self._input.returnPressed.connect(self._send_message)
        input_layout.addWidget(self._input)

        self._send_button = QPushButton("enviar")
        self._send_button.setObjectName("chat-send")
        self._send_button.setStyleSheet(
            f"""
            QPushButton {{
                background: {self._theme.red};
                color: {self._theme.text};
                border: none;
                border-radius: {self._theme.radius_sm};
                font-family: {self._theme.mono};
                font-size: 12px;
                font-weight: bold;
                padding: 10px 20px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{
                background: {self._theme.red_bright};
            }}
            QPushButton:pressed {{
                background: {self._theme.red_deep};
            }}
            QPushButton:disabled {{
                background: {self._theme.graphite};
                color: {self._theme.faint};
            }}
            """
        )
        self._send_button.clicked.connect(self._send_message)
        input_layout.addWidget(self._send_button)

        # Botão nova conversa
        self._new_button = QPushButton("nova conversa")
        self._new_button.setObjectName("chat-new")
        self._new_button.setStyleSheet(
            f"""
            QPushButton {{
                background: {self._theme.panel_solid};
                color: {self._theme.muted};
                border: 1px solid {self._theme.line};
                border-radius: {self._theme.radius_sm};
                font-family: {self._theme.mono};
                font-size: 11px;
                padding: 8px 16px;
                text-transform: uppercase;
            }}
            QPushButton:hover {{
                border: 1px solid {self._theme.red_bright};
                color: {self._theme.text};
            }}
            """
        )
        self._new_button.clicked.connect(self._new_conversation)
        input_layout.addWidget(self._new_button)

        layout.addLayout(input_layout)

    # -- mensagens ----------------------------------------------------------
    def append_message(self, role: str, content: str, provider: str | None = None, model: str | None = None) -> None:
        """Acrescenta uma mensagem ao histórico."""
        role_colors = {
            "user": self._theme.muted,
            "assistant": self._theme.text,
            "system": self._theme.warn,
            "tool": self._theme.ok,
        }
        color = role_colors.get(role, self._theme.text)

        html = self._history.toHtml()
        prefix = ""
        if role == "user":
            prefix = f'<span style="color:{self._theme.muted}">[você]</span> '
        elif role == "assistant":
            provider_tag = f" <span style='color:{self._theme.faint};font-size:10px'>[{provider or '?'}]</span>" if provider else ""
            model_tag = f" <span style='color:{self._theme.faint};font-size:10px'>{model}</model>" if model else ""
            prefix = f'<span style="color:{self._theme.red_bright}">[ultron]</span>{provider_tag}{model_tag} '
        elif role == "tool":
            prefix = f'<span style="color:{self._theme.ok}">[ferramenta]</span> '

        escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        escaped = escaped.replace("\n", "<br>")

        new_html = (
            f'<div style="margin:8px 0; line-height:1.5;">'
            f'{prefix}<span style="color:{color}">{escaped}</span>'
            f'</div>'
        )

        self._history.setHtml(html + new_html)
        self._history.verticalScrollBar().setValue(
            self._history.verticalScrollBar().maximum()
        )

    def set_processing(self, processing: bool) -> None:
        """Define se o chat está processando uma mensagem."""
        self._processing = processing
        self._input.setEnabled(not processing)
        self._send_button.setEnabled(not processing)
        self._status_label.setText("processando..." if processing else "pronto")
        self._status_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self._theme.red_bright if processing else self._theme.muted};
                font-family: {self._theme.mono};
                font-size: 11px;
                margin-right: 8px;
            }}
            """
        )

    def show_error(self, message: str) -> None:
        """Exibe um erro no chat."""
        self.append_message("system", f"erro: {message}")
        self.error_occurred.emit(message)
        self.set_processing(False)

    def show_tool_result(self, tool_name: str, result: str) -> None:
        """Exibe o resultado de uma ferramenta."""
        self.append_message("tool", f"{tool_name}: {result}")
        self.tool_called.emit(tool_name, result)

    # -- ações --------------------------------------------------------------
    def _send_message(self) -> None:
        text = self._input.text().strip()
        if not text or self._processing:
            return

        self.append_message("user", text)
        self._input.clear()
        self.set_processing(True)

        # Usa o adapter para enviar ao núcleo (síncrono, mas rápido)
        try:
            response = self._adapter.process_text(text)
            self._handle_response(response)
        except Exception as exc:  # noqa: BLE001
            self.show_error(str(exc))

    def _handle_response(self, response: Any) -> None:
        """Processa a resposta do OrchestratorBridge."""
        content = getattr(response, "content", str(response))
        provider = getattr(response, "provider", None)
        model = getattr(response, "model", None)
        tool_calls = getattr(response, "tool_calls", None) or []

        self.append_message("assistant", content, provider=provider, model=model)

        for tc in tool_calls:
            tc_name = tc.get("tool", tc) if isinstance(tc, dict) else str(tc)
            self.show_tool_result(tc_name, "executado")

        self.set_processing(False)
        self.message_sent.emit(content)

    def _new_conversation(self) -> None:
        """Inicia uma nova conversa."""
        try:
            self._adapter.new_conversation()
            self._history.clear()
            self._conversation_id = None
            self.append_message("system", "nova conversa iniciada")
        except Exception as exc:  # noqa: BLE001
            self.show_error(str(exc))

    def load_history(self, messages: list[dict[str, Any]]) -> None:
        """Carrega o histórico de mensagens."""
        self._history.clear()
        for msg in messages:
            role = msg.get("role", "system")
            content = msg.get("content", "")
            provider = msg.get("provider")
            model = msg.get("model")
            self.append_message(role, content, provider=provider, model=model)


# Importação tardia para type hints
from typing import Any  # noqa: E402


__all__ = ["ChatWidget"]
