"""Sistema visual e avatar do ULTRON (INTERFACE.md §7).

Reproduz o sistema visual original do Mark LVI:
- Avatar central com animação holográfica
- Estados vinculados a eventos reais do ULTRON
- Máquina de estados visual centralizada:
  IDLE, LISTENING, PROCESSING, PLANNING, EXECUTING, SPEAKING,
  WAITING_CONFIRMATION, INTERRUPTED, ERROR, OFFLINE

Sem rosto robótico: identidade digital abstrata.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..animations.holographic_canvas import AssistantState, HolographicCanvas
from ..themes.ultron_theme import UltronTheme


class AvatarWidget(QWidget):
    """Avatar central com animação holográfica e indicador de estado."""

    def __init__(self, theme: UltronTheme | None = None, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme or UltronTheme()
        self._state = AssistantState.IDLE
        self._state_label: Optional[QLabel] = None
        self._detail_label: Optional[QLabel] = None
        self._canvas: Optional[HolographicCanvas] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("avatar-widget")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Canvas holográfico
        self._canvas = HolographicCanvas(theme=self._theme, parent=self)
        self._canvas.setFixedSize(260, 260)
        layout.addWidget(self._canvas, alignment=Qt.AlignCenter)

        # Estado (texto, acessibilidade)
        self._state_label = QLabel("inicializando")
        self._state_label.setObjectName("avatar-state")
        self._state_label.setAlignment(Qt.AlignCenter)
        self._state_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self._theme.text};
                font-family: {self._theme.mono};
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 2px;
                text-transform: uppercase;
            }}
            """
        )
        layout.addWidget(self._state_label, alignment=Qt.AlignCenter)

        # Detalhe
        self._detail_label = QLabel("ULTRON 2.0")
        self._detail_label.setObjectName("avatar-detail")
        self._detail_label.setAlignment(Qt.AlignCenter)
        self._detail_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self._theme.muted};
                font-family: {self._theme.mono};
                font-size: 11px;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            """
        )
        layout.addWidget(self._detail_label, alignment=Qt.AlignCenter)

    # -- estado -------------------------------------------------------------
    def set_state(self, state: str, detail: str | None = None) -> None:
        """Atualiza o estado visual do avatar."""
        self._state = AssistantState(state)
        if self._canvas is not None:
            self._canvas.set_state(state)

        # Mapeia estado para texto em português
        state_texts = {
            AssistantState.IDLE: "inativo",
            AssistantState.LISTENING: "ouvindo",
            AssistantState.PROCESSING: "processando",
            AssistantState.PLANNING: "planejando",
            AssistantState.EXECUTING: "executando",
            AssistantState.SPEAKING: "falando",
            AssistantState.WAITING_CONFIRMATION: "aguardando confirmação",
            AssistantState.INTERRUPTED: "interrompido",
            AssistantState.ERROR: "erro",
            AssistantState.OFFLINE: "offline",
        }

        if self._state_label is not None:
            self._state_label.setText(state_texts.get(self._state, state))

        if detail is not None and self._detail_label is not None:
            self._detail_label.setText(detail)

        # Cor do estado também reflete no texto
        color = self._canvas._state_color() if self._canvas else None
        if color is not None and self._state_label is not None:
            self._state_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {color.name()};
                    font-family: {self._theme.mono};
                    font-size: 13px;
                    font-weight: bold;
                    letter-spacing: 2px;
                    text-transform: uppercase;
                }}
                """
            )

    def set_audio_level(self, level: float) -> None:
        """Atualiza o nível de áudio (captura ou reprodução)."""
        if self._canvas is not None:
            self._canvas.set_audio_level(level)

    def state(self) -> str:
        return str(self._state)


# Permite importação direta do QLabel para type hints
from typing import Optional  # noqa: E402


__all__ = ["AvatarWidget", "AssistantState"]
