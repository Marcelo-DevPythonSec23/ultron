"""StateTracker — rastreamento e persistência de estado de workflows (Fase 7).

Permite salvar o estado de um workflow (passos, resultados, tentativas) para
recuperação após falhas e retomada de trabalhos interrompidos
(AGENTS.md §4.7: persistência de estado, recuperação após falhas).

Não persiste credenciais nem conteúdo sensível: apenas metadados de execução.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import StepDependency, StepState, Workflow, WorkflowState, WorkflowStep

logger = logging.getLogger("ultron2.autonomy.state")


class StateTracker:
    """Acompanha e persiste o estado de workflows em execução."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._state_dir = Path(state_dir) if state_dir else Path(
            Path.home() / ".ultron2" / "autonomy_state"
        )
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._workflows: dict[str, Workflow] = {}
        self._lock = threading.RLock()

    # -- ciclo de vida --------------------------------------------------------
    def register(self, workflow: Workflow) -> None:
        with self._lock:
            self._workflows[workflow.id] = workflow
        self._persist(workflow)
        logger.info("workflow registrado: %s (estado=%s)", workflow.id, workflow.state.value)

    def get(self, workflow_id: str) -> Workflow | None:
        with self._lock:
            return self._workflows.get(workflow_id)

    def update(self, workflow: Workflow) -> None:
        with self._lock:
            self._workflows[workflow.id] = workflow
        self._persist(workflow)

    def remove(self, workflow_id: str) -> bool:
        with self._lock:
            wf = self._workflows.pop(workflow_id, None)
        if wf is None:
            return False
        try:
            (self._state_dir / f"{workflow_id}.json").unlink()
        except FileNotFoundError:
            pass
        logger.info("workflow removido: %s", workflow_id)
        return True

    def list_workflows(self) -> list[Workflow]:
        with self._lock:
            return list(self._workflows.values())

    def load_all(self) -> int:
        """Carrega workflows persistidos do disco (recuperação após reinício)."""
        loaded = 0
        with self._lock:
            for path in sorted(self._state_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    wf = self._deserialize(data)
                    self._workflows[wf.id] = wf
                    loaded += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("falha ao carregar estado de %s: %s", path, exc)
        logger.info("workflows carregados do estado persistido: %d", loaded)
        return loaded

    # -- persistência ---------------------------------------------------------
    def _persist(self, workflow: Workflow) -> None:
        try:
            path = self._state_dir / f"{workflow.id}.json"
            path.write_text(
                json.dumps(self._serialize(workflow), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("falha ao persistir estado do workflow %s: %s", workflow.id, exc)

    # -- serialização ---------------------------------------------------------
    @staticmethod
    def _serialize(workflow: Workflow) -> dict[str, Any]:
        return {
            "id": workflow.id,
            "objective": workflow.objective,
            "description": workflow.description,
            "state": workflow.state.value,
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "error": workflow.error,
            "max_steps": workflow.max_steps,
            "max_execution_seconds": workflow.max_execution_seconds,
            "require_human_approval": workflow.require_human_approval,
            "steps": [
                {
                    "id": s.id,
                    "objective": s.objective,
                    "description": s.description,
                    "target": s.target,
                    "target_type": s.target_type,
                    "context": s.context,
                    "dependencies": [
                        {"step_id": d.step_id, "mode": d.mode} for d in s.dependencies
                    ],
                    "permissions": s.permissions,
                    "max_attempts": s.max_attempts,
                    "attempts": s.attempts,
                    "state": s.state.value,
                    "result": s.result,
                    "error": s.error,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "execution_seconds": s.execution_seconds,
                }
                for s in workflow.steps
            ],
        }

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> Workflow:
        steps = []
        for s in data.get("steps", []):
            steps.append(
                WorkflowStep(
                    id=s["id"],
                    objective=s["objective"],
                    description=s.get("description", ""),
                    target=s["target"],
                    target_type=s.get("target_type", "agent"),
                    context=s.get("context", {}),
                    dependencies=[
                        StepDependency(step_id=d["step_id"], mode=d.get("mode", "success"))
                        for d in s.get("dependencies", [])
                    ],
                    permissions=s.get("permissions", []),
                    max_attempts=s.get("max_attempts", 3),
                    attempts=s.get("attempts", 0),
                    state=StepState(s.get("state", "pending")),
                    result=s.get("result"),
                    error=s.get("error"),
                    started_at=datetime.fromisoformat(s["started_at"]) if s.get("started_at") else None,
                    completed_at=datetime.fromisoformat(s["completed_at"]) if s.get("completed_at") else None,
                    execution_seconds=s.get("execution_seconds"),
                )
            )
        return Workflow(
            id=data["id"],
            objective=data["objective"],
            description=data.get("description", ""),
            steps=steps,
            state=WorkflowState(data.get("state", "pending")),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now(timezone.utc).isoformat())
            ),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error"),
            max_steps=data.get("max_steps", 50),
            max_execution_seconds=data.get("max_execution_seconds", 3600.0),
            require_human_approval=data.get("require_human_approval", False),
        )

    def public(self) -> dict[str, Any]:
        return {
            "workflows": {
                wid: wf.to_public_dict() for wid, wf in self._workflows.items()
            },
            "total": len(self._workflows),
            "by_state": {
                state.value: sum(1 for w in self._workflows.values() if w.state == state)
                for state in WorkflowState
            },
        }
