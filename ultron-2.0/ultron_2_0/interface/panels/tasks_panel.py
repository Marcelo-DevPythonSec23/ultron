"""Painel Tasks - operações em execução (INTERFACE.md §11).

Apresenta as operações realmente existentes no ULTRON:
- Ferramentas em execução, concluídas, com falha, pendentes
- Operações aguardando confirmação
- Estado das tarefas, tempo de execução, resultado resumido

Respeita os estados reais do ToolResult: done, unverified, failed, started.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..adapters.bridge_adapter import BridgeAdapter
from ..themes.ultron_theme import UltronTheme


class TaskItem(QFrame):
    """Uma tarefa individual com estado e resultado."""

    STATE_COLORS = {
        "pending": "#9a9490",
        "started": "#ffb020",
        "done": "#3ddc97",
        "unverified": "#ffb020",
        "failed": "#ff5a66",
    }

    def __init__(self, task_id: str, parent=None) -> None:
        super().__init__(parent)
        self._task_id = task_id
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("task-item")
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        self._id_label = QLabel(self._task_id[:12])
        self._id_label.setStyleSheet(
            f"color: {{}}; font-size: 12px; font-family: mono;".format("#6d6864")
        )
        layout.addWidget(self._id_label)

        self._name_label = QLabel("")
        self._name_label.setStyleSheet(
            f"color: {{}}; font-size: 13px; font-family: sans;".format("#ece9e6")
        )
        layout.addWidget(self._name_label, stretch=1)

        self._state_label = QLabel("pending")
        self._state_label.setObjectName("task-state")
        self._state_label.setStyleSheet(
            f"color: {{}}; font-size: 11px; font-family: mono; font-weight: bold;".format(
                "#9a9490"
            )
        )
        layout.addWidget(self._state_label)

        self._result_label = QLabel("")
        self._result_label.setObjectName("task-result")
        self._result_label.setStyleSheet(
            f"color: {{}}; font-size: 11px; font-family: mono;".format("#6d6864")
        )
        layout.addWidget(self._result_label)

    def update(self, name: str, state: str, result: str | None = None) -> None:
        self._name_label.setText(name)
        self._state_label.setText(state)

        color = self.STATE_COLORS.get(state, "#9a9490")
        self._state_label.setStyleSheet(
            f"color: {color}; font-size: 11px; font-family: mono; font-weight: bold;"
        )

        if result is not None:
            self._result_label.setText(result[:40])


class TasksPanel(QWidget):
    """Painel de tarefas do ULTRON."""

    def __init__(
        self,
        adapter: BridgeAdapter,
        theme=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._theme = theme
        self._tasks: dict[str, TaskItem] = {}
        self._setup_ui()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(3000)

    def _setup_ui(self) -> None:
        self.setObjectName("tasks-panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("tasks")
        title.setStyleSheet(
            "color: #ff2f3d; font-size: 16px; font-weight: bold; font-family: mono; text-transform: uppercase; margin-bottom: 8px;"
        )
        layout.addWidget(title)

        self._list_layout = QVBoxLayout()
        self._list_layout.setSpacing(6)
        layout.addLayout(self._list_layout)
        layout.addStretch()

    def refresh(self) -> None:
        """Atualiza as tarefas a partir do bridge."""
        try:
            # Tenta obter tarefas via agent_orchestrator (Fase 7)
            runtime = self._adapter._bridge.runtime
            if runtime is None or runtime.agent_orchestrator is None:
                return

            agent_orch = runtime.agent_orchestrator
            # Obtém tarefas através do queue
            tasks = agent_orch._queue.all_tasks() if agent_orch._queue else []
            self._apply_tasks(tasks)
        except Exception:  # noqa: BLE001
            pass

    def _apply_tasks(self, tasks: list[Any]) -> None:
        # Remove itens que não existem mais
        current_ids = {t.id for t in tasks}
        for tid in list(self._tasks.keys()):
            if tid not in current_ids:
                item = self._tasks.pop(tid)
                self._list_layout.removeWidget(item)
                item.deleteLater()

        # Adiciona/atualiza itens
        for task in tasks:
            if task.id not in self._tasks:
                item = TaskItem(task.id, parent=self)
                self._tasks[task.id] = item
                self._list_layout.addWidget(item)

            item = self._tasks[task.id]
            result_text = None
            if task.result is not None:
                result_text = str(task.result)[:40]
            item.update(task.description, task.state.value, result_text)


__all__ = ["TasksPanel"]
