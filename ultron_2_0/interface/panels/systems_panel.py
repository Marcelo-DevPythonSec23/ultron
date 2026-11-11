"""Painel Systems - monitoramento em tempo real (INTERFACE.md §10).

Exibe métricas reais do sistema via OrchestratorBridge (/api/system):
CPU, RAM, temperatura, GPU, uptime, processos, estado do núcleo e providers.

Não inventa métricas: quando um sensor não está disponível, mostra
indisponibilidade em vez de valores fictícios.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..adapters.bridge_adapter import BridgeAdapter
from ..themes.ultron_theme import UltronTheme


class MetricWidget(QFrame):
    """Um medidor individual com valor, rótulo e estado."""

    def __init__(self, label: str, unit: str = "", parent=None) -> None:
        super().__init__(parent)
        self._label = label
        self._unit = unit
        self._value = "—"
        self._status = "indisponível"  # disponível, atenção, crítico, indisponível
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("metric-widget")
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        self._label_widget = QLabel(self._label)
        self._label_widget.setStyleSheet(
            f"color: {{}}; font-size: 11px; font-family: mono; text-transform: uppercase;".format(
                "#9a9490"
            )
        )
        layout.addWidget(self._label_widget)

        self._value_widget = QLabel(self._value)
        self._value_widget.setObjectName("metric-value")
        self._value_widget.setStyleSheet(
            "color: #ece9e6; font-size: 20px; font-weight: bold; font-family: mono;"
        )
        layout.addWidget(self._value_widget)

        self._unit_widget = QLabel(self._unit)
        self._unit_widget.setStyleSheet(
            "color: #6d6864; font-size: 11px; font-family: mono;"
        )
        layout.addWidget(self._unit_widget)

        self._status_widget = QLabel(self._status)
        self._status_widget.setObjectName("metric-status")
        self._status_widget.setStyleSheet(
            "color: #6d6864; font-size: 10px; font-family: mono;"
        )
        layout.addWidget(self._status_widget)

    def set_value(self, value: Any, unit: str | None = None, status: str = "disponível") -> None:
        self._value = str(value)
        if unit is not None:
            self._unit = unit
        self._status = status
        self._value_widget.setText(f"{self._value} {self._unit}".strip())
        self._status_widget.setText(self._status)

        # Cor do status
        status_colors = {
            "disponível": "#3ddc97",
            "atenção": "#ffb020",
            "crítico": "#ff5a66",
            "indisponível": "#6d6864",
        }
        color = status_colors.get(status, "#6d6864")
        self._status_widget.setStyleSheet(
            f"color: {color}; font-size: 10px; font-family: mono;"
        )


class SystemsPanel(QWidget):
    """Painel de monitoramento do sistema com métricas reais."""

    def __init__(
        self,
        adapter: BridgeAdapter,
        theme=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._theme = theme
        self._metrics: dict[str, MetricWidget] = {}
        self._setup_ui()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(5000)  # atualiza a cada 5s

    def _setup_ui(self) -> None:
        self.setObjectName("systems-panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Título
        title = QLabel("systems")
        title.setStyleSheet(
            "color: #ff2f3d; font-size: 16px; font-weight: bold; font-family: mono; text-transform: uppercase; margin-bottom: 8px;"
        )
        layout.addWidget(title)

        # Grid de métricas
        self._grid = QGridLayout()
        self._grid.setSpacing(10)
        layout.addLayout(self._grid)

        # Métricas padrão (serão preenchidas no primeiro refresh)
        self._create_metric("cpu", "CPU", "%")
        self._create_metric("ram", "RAM", "%")
        self._create_metric("temp", "TEMP", "°C")
        self._create_metric("gpu", "GPU", "%")
        self._create_metric("uptime", "UPTIME", "")
        self._create_metric("procs", "PROCESSOS", "")

        layout.addStretch()

    def _create_metric(self, key: str, label: str, unit: str) -> None:
        row = len(self._metrics) // 3
        col = len(self._metrics) % 3
        widget = MetricWidget(label, unit)
        self._grid.addWidget(widget, row, col)
        self._metrics[key] = widget

    def refresh(self) -> None:
        """Atualiza as métricas a partir do bridge (dados reais)."""
        try:
            runtime = self._adapter._bridge.runtime
            if runtime is None:
                return

            # Tenta obter métricas via system_snapshot (marklvi_actions)
            from ultron_2_0.marklvi_actions import system_snapshot

            import asyncio

            try:
                metrics = asyncio.to_thread(system_snapshot)
                # system_snapshot é síncrono, não precisa de await
                metrics = system_snapshot()
            except Exception:
                metrics = None

            if metrics:
                self._apply_metrics(metrics)
        except Exception as exc:  # noqa: BLE001
            # Sem métricas disponíveis: mostra indisponível
            for widget in self._metrics.values():
                widget.set_value("—", status="indisponível")

    def _apply_metrics(self, metrics: dict[str, Any]) -> None:
        """Aplica métricas aos widgets."""
        # Mapeia chaves do snapshot para widgets
        mapping = {
            "cpu_percent": ("cpu", "%", "disponível"),
            "ram_percent": ("ram", "%", "disponível"),
            "cpu_temp_c": ("temp", "°C", "disponível"),
            "gpu_percent": ("gpu", "%", "disponível"),
            "uptime": ("uptime", "", "disponível"),
            "process_count": ("procs", "", "disponível"),
        }

        for key, (widget_key, unit, status) in mapping.items():
            if key in metrics and widget_key in self._metrics:
                value = metrics[key]
                # Limiares de cor
                widget_status = status
                if isinstance(value, (int, float)):
                    if key in ("cpu_percent", "ram_percent", "gpu_percent"):
                        if value >= 85:
                            widget_status = "crítico"
                        elif value >= 65:
                            widget_status = "atenção"
                    elif key == "cpu_temp_c":
                        if value >= 85:
                            widget_status = "crítico"
                        elif value >= 65:
                            widget_status = "atenção"

                self._metrics[widget_key].set_value(value, unit, widget_status)


__all__ = ["SystemsPanel"]
