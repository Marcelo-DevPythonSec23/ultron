"""Canvas holográfico abstrato (INTERFACE.md §7).

Canvas desenhado por QPainter que reage a estados reais do ULTRON:
IDLE, LISTENING, PROCESSING, PLANNING, EXECUTING, SPEAKING,
WAITING_CONFIRMATION, INTERRUPTED, ERROR, OFFLINE.

Sem avatares de rostos robóticos: identidade digital abstrata, conforme
definido no INTERFACE.md. Todas as informações existem também em texto
(acessibilidade).
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from ..themes.ultron_theme import UltronTheme


class AssistantState(str):
    """Estados visuais do assistente (INTERFACE.md §7)."""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


class HolographicCanvas(QWidget):
    """Canvas abstrato com animações sutis de monitoramento.

    Desenha:
    - Grade de pontos em camada cacheada
    - Anéis concêntricos com dash e rotação
    - Núcleo pulsante com gradiente radial
    - Marcas radiais
    - Reação ao estado atual (cor e velocidade)
    """

    def __init__(self, theme: UltronTheme | None = None, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme or UltronTheme()
        self._state = AssistantState.IDLE
        self._angle = 0.0
        self._pulse = 0.0
        self._audio_level = 0.0
        self._grid_cache: Optional[object] = None

        # Timer de animação (60 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 FPS

        self.setMinimumSize(300, 300)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)

    # -- estado -------------------------------------------------------------
    def set_state(self, state: str) -> None:
        self._state = AssistantState(state)
        self.update()

    def set_audio_level(self, level: float) -> None:
        """Nível de áudio 0..1 (captura ou reprodução)."""
        self._audio_level = max(0.0, min(1.0, level))
        self.update()

    def state(self) -> str:
        """Retorna o estado atual do avatar."""
        return self._state.value

    # -- animação -----------------------------------------------------------
    def _tick(self) -> None:
        self._angle = (self._angle + 2.0) % 360.0
        speed = self._pulse_speed()
        self._pulse = (self._pulse + speed) % (2 * math.pi)
        self.update()

    def _pulse_speed(self) -> float:
        speeds = {
            AssistantState.IDLE: 0.02,
            AssistantState.LISTENING: 0.08,
            AssistantState.PROCESSING: 0.12,
            AssistantState.PLANNING: 0.10,
            AssistantState.EXECUTING: 0.14,
            AssistantState.SPEAKING: 0.16,
            AssistantState.WAITING_CONFIRMATION: 0.06,
            AssistantState.INTERRUPTED: 0.20,
            AssistantState.ERROR: 0.18,
            AssistantState.OFFLINE: 0.01,
        }
        return speeds.get(self._state, 0.02)

    def _state_color(self) -> QColor:
        colors = {
            AssistantState.IDLE: QColor(self._theme.faint),
            AssistantState.LISTENING: QColor(self._theme.red_bright),
            AssistantState.PROCESSING: QColor(self._theme.red),
            AssistantState.PLANNING: QColor(self._theme.warn),
            AssistantState.EXECUTING: QColor(self._theme.red),
            AssistantState.SPEAKING: QColor(self._theme.ok),
            AssistantState.WAITING_CONFIRMATION: QColor(self._theme.warn),
            AssistantState.INTERRUPTED: QColor(self._theme.err),
            AssistantState.ERROR: QColor(self._theme.err),
            AssistantState.OFFLINE: QColor(self._theme.faint),
        }
        return colors.get(self._state, QColor(self._theme.faint))

    # -- pintura ------------------------------------------------------------
    def paintEvent(self, event) -> None:  # type: ignore[override]
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            rect = self.rect()
            center = QPointF(rect.width() / 2, rect.height() / 2)
            size = min(rect.width(), rect.height())

            # Fundo do canvas
            painter.fillRect(rect, QColor(self._theme.panel_solid))

            # Cor do estado
            color = self._state_color()

            # 1. Grade de pontos (sutis, camada de fundo)
            self._draw_grid(painter, rect, size)

            # 2. Anéis concêntricos rotativos
            self._draw_rings(painter, center, size, color)

            # 3. Núcleo pulsante
            self._draw_core(painter, center, size, color)

            # 4. Marcas radiais
            self._draw_radial_marks(painter, center, size, color)

            # 5. Indicador de nível de áudio (quando houver)
            if self._audio_level > 0.05:
                self._draw_audio_level(painter, center, size, color)
        except Exception:  # noqa: BLE001 — pintura nunca deve derrubar a UI
            pass

    def _draw_grid(self, painter: QPainter, rect: QRectF, size: float) -> None:
        """Grade de pontos em camada cacheada."""
        pen = QPen(QColor(self._theme.line))
        pen.setWidth(1)
        painter.setPen(pen)

        step = 20.0
        offset = self._angle * 0.1
        left = int(rect.left())
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())
        for x in range(left, right, int(step)):
            for y in range(top, bottom, int(step)):
                dx = x - rect.center().x()
                dy = y - rect.center().y()
                dist = math.hypot(dx, dy)
                if dist < size * 0.6:
                    alpha = int(40 + 20 * math.sin(dist * 0.1 + offset))
                    color = QColor(self._theme.line)
                    color.setAlpha(max(0, min(255, alpha)))
                    pen.setColor(color)
                    pen.setWidth(1)
                    painter.setPen(pen)
                    painter.drawPoint(x, y)

    def _draw_rings(self, painter: QPainter, center: QPointF, size: float, color: QColor) -> None:
        """Anéis concêntricos rotativos."""
        for i in range(3):
            radius = size * (0.35 + 0.15 * i)
            pen = QPen(color)
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            pen.setDashPattern([8, 6, 2, 6])
            alpha = int(120 - 40 * i)
            color_alpha = QColor(color)
            color_alpha.setAlpha(max(0, min(255, alpha)))
            pen.setColor(color_alpha)
            painter.setPen(pen)

            start_angle = int(self._angle * 16 * (1 + i * 0.5))
            span_angle = int(120 * 16)
            painter.drawArc(
                QRectF(
                    center.x() - radius,
                    center.y() - radius,
                    radius * 2,
                    radius * 2,
                ),
                start_angle,
                span_angle,
            )

    def _draw_core(self, painter: QPainter, center: QPointF, size: float, color: QColor) -> None:
        """Núcleo pulsante com gradiente radial."""
        pulse = (math.sin(self._pulse) + 1) / 2  # 0..1
        base_radius = size * 0.18
        pulse_radius = base_radius * (1 + 0.25 * pulse)

        # Gradiente radial
        gradient = QRadialGradient(center, pulse_radius)
        color_inner = QColor(color)
        color_inner.setAlpha(220)
        color_outer = QColor(color)
        color_outer.setAlpha(60)
        gradient.setColorAt(0, color_inner)
        gradient.setColorAt(1, color_outer)

        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(
            QPointF(center.x(), center.y()), pulse_radius, pulse_radius
        )

        # Contorno do núcleo
        pen = QPen(color)
        pen.setWidth(2)
        pen.setAlpha(180)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            QPointF(center.x(), center.y()), pulse_radius, pulse_radius
        )

    def _draw_radial_marks(self, painter: QPainter, center: QPointF, size: float, color: QColor) -> None:
        """Marcas radiais ao redor do núcleo."""
        pen = QPen(color)
        pen.setWidth(1)
        pen.setAlpha(100)
        painter.setPen(pen)

        num_marks = 12
        for i in range(num_marks):
            angle = math.radians(i * 30 + self._angle * 0.5)
            r1 = size * 0.45
            r2 = size * 0.55
            x1 = center.x() + r1 * math.cos(angle)
            y1 = center.y() + r1 * math.sin(angle)
            x2 = center.x() + r2 * math.cos(angle)
            y2 = center.y() + r2 * math.sin(angle)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_audio_level(self, painter: QPainter, center: QPointF, size: float, color: QColor) -> None:
        """Indicador de nível de áudio (captura ou reprodução)."""
        pen = QPen(color)
        pen.setWidth(3)
        pen.setAlpha(200)
        painter.setPen(pen)

        radius = size * 0.62
        start_angle = 0
        span_angle = int(360 * self._audio_level * 16)
        painter.drawArc(
            QRectF(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
            ),
            start_angle,
            span_angle,
        )


__all__ = ["HolographicCanvas", "AssistantState"]
