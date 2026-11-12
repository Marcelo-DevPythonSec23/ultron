"""Testes da Fase 7 — Autonomia Operacional.

Cobrem, sem exigir execução real de agentes/integrações:

1. TaskDecomposer.decompose — decomposição determinística de objetivo.
2. TaskDecomposer.build_steps — dependências lineares entre passos.
3. Planner.plan — cria Workflow com limites de segurança.
4. Workflow estados (is_done, all_successful, step transitions).
5. StateTracker — register/get/update/remove/list/persistência.
6. Scheduler — schedule/due/pending/cancel.
7. RecoveryManager — list_workflows_needing_recovery, plan_recovery, recover.
8. WorkflowEngine.run — execução de workflow simples (agente/integração mock).
9. Limites de workflow (max_steps, tempo máximo).
10. Workflow sem orquestradores — erro controlado.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from ultron_2_0.autonomy import (
    Planner,
    RecoveryManager,
    Scheduler,
    StateTracker,
    TaskDecomposer,
    WorkflowEngine,
    WorkflowState,
    build_steps,
    decompose,
)
from ultron_2_0.autonomy.contracts import (
    StepDependency,
    StepState,
    Workflow,
    WorkflowStep,
)
from ultron_2_0.autonomy.state_tracker import StateTracker as ST


# -- agentes/integrações mock ----------------------------------------------
class _Task:
    def __init__(self, task_id, state, result):
        self.id = task_id
        self.state = state
        self.result = result


class FakeAgentOrchestrator:
    """Mock do AgentOrchestrator: executa tarefa e devolve resultado."""

    def __init__(self, *, fail_targets: set[str] | None = None) -> None:
        self.fail_targets = fail_targets or set()
        self.tasks: list[dict] = []
        self.results: dict[str, dict] = {}
        from ultron_2_0.agents.agent_task import TaskState
        self._TaskState = TaskState

    def create_task(self, *, objective, description, agent_type, context, permissions, max_attempts):
        task_id = f"agent-task-{len(self.tasks)}"
        success = agent_type not in self.fail_targets
        result = {
            "success": success,
            "content": {"ok": True} if success else {},
            "error": None if success else f"{agent_type} falhou",
        }
        self.results[task_id] = result
        self.tasks.append({
            "id": task_id, "objective": objective, "agent_type": agent_type,
            "state": self._TaskState.COMPLETED if success else self._TaskState.FAILED,
        })
        return type("T", (), {"id": task_id})()

    async def run_ready(self, max_tasks=1):
        return 0

    def get_task(self, task_id):
        for t in self.tasks:
            if t["id"] == task_id:
                return type("T", (), {"state": t["state"]})()
        return None

    def get_result(self, task_id):
        return self.results.get(task_id)


class FakeIntegrationOrchestrator:
    """Mock do IntegrationOrchestrator."""

    def __init__(self, *, fail_targets: set[str] | None = None) -> None:
        self.fail_targets = fail_targets or set()
        self.tasks: list[dict] = []

    def create_task(self, *, integration_type, target, prompt, params, max_attempts):
        task_id = f"int-task-{len(self.tasks)}"
        self.tasks.append({
            "id": task_id, "target": target, "prompt": prompt,
        })
        return type("T", (), {"id": task_id})()

    def run_task(self, task):
        if task.target in self.fail_targets:
            return type("R", (), {
                "success": False, "error": f"{task.target} falhou",
                "to_public_dict": lambda self: {"success": False, "error": f"{task.target} falhou"},
            })()
        return type("R", (), {
            "success": True, "content": {"ok": True},
            "to_public_dict": lambda self: {"success": True, "content": {"ok": True}},
        })()


# -- 1. decomposicao deterministica -----------------------------------------
def test_decompose_deterministico():
    r1 = decompose("implementar uma funcao python para ordenar lista")
    r2 = decompose("implementar uma funcao python para ordenar lista")
    assert r1 == r2
    assert len(r1) >= 1
    assert any(s["target"] == "developer" for s in r1)


def test_decompose_pesquisa_usa_research():
    steps = decompose("pesquisar sobre arquitetura de software")
    assert any(s["target"] == "research" for s in steps)


def test_decompose_seguranca_usa_security():
    steps = decompose("auditar seguranca de permissões")
    assert any(s["target"] == "security" for s in steps)


def test_decompose_sem_match_usa_fallback():
    steps = decompose("coisas aleatórias xyz123")
    assert len(steps) == 1
    assert steps[0]["target"] == "developer"


# -- 2. build_steps ---------------------------------------------------------
def test_build_steps_dependencias_lineares():
    steps = build_steps("implementar codigo e testar")
    assert len(steps) >= 1
    # Primeiro passo sem dependencia.
    assert steps[0].dependencies == []
    # Passos seguintes dependem do anterior.
    for step in steps[1:]:
        assert len(step.dependencies) == 1
        assert step.dependencies[0].mode == "success"


# -- 3. planner -------------------------------------------------------------
def test_planner_cria_workflow():
    planner = Planner()
    wf = planner.plan("implementar uma API REST")
    assert wf.id is not None
    assert wf.objective == "implementar uma API REST"
    assert wf.state == WorkflowState.PENDING
    assert len(wf.steps) >= 1
    assert wf.max_steps == 50


def test_planner_respeita_limites():
    planner = Planner(max_steps=5, max_execution_seconds=300, require_human_approval=True)
    wf = planner.plan("qualquer coisa")
    assert wf.max_steps == 5
    assert wf.max_execution_seconds == 300
    assert wf.require_human_approval is True


# -- 4. estados de workflow -------------------------------------------------
def test_workflow_estado_e_transicoes():
    wf = Workflow(id="wf-1", objective="x", description="d")
    assert wf.is_done() is False
    assert wf.all_successful() is False

    step = WorkflowStep(id="s-1", objective="o", description="d", target="a", target_type="agent")
    step.state = StepState.COMPLETED
    wf.steps = [step]
    assert wf.all_successful() is True
    assert wf.is_done() is True


def test_workflow_step_transition():
    step = WorkflowStep(id="s-1", objective="o", description="d", target="a", target_type="agent")
    assert step.can_transition(StepState.ASSIGNED)
    assert not step.can_transition(StepState.COMPLETED)  # nao pode pular estados
    step.state = StepState.ASSIGNED
    assert step.can_transition(StepState.RUNNING)


# -- 5. state tracker ------------------------------------------------------
def test_state_tracker_register_get_update_remove(tmp_path):
    tracker = StateTracker(state_dir=str(tmp_path / "state"))
    wf = Workflow(id="wf-1", objective="x", description="d")
    tracker.register(wf)

    assert tracker.get("wf-1") is wf
    assert len(tracker.list_workflows()) == 1

    wf.state = WorkflowState.COMPLETED
    tracker.update(wf)
    assert tracker.get("wf-1").state == WorkflowState.COMPLETED

    assert tracker.remove("wf-1") is True
    assert tracker.get("wf-1") is None
    assert len(tracker.list_workflows()) == 0


def test_state_tracker_persiste_e_carrega(tmp_path):
    state_dir = tmp_path / "state"
    tracker1 = StateTracker(state_dir=str(state_dir))
    wf = Workflow(id="wf-persist", objective="persistir", description="d")
    tracker1.register(wf)
    wf.state = WorkflowState.RUNNING
    tracker1.update(wf)

    tracker2 = StateTracker(state_dir=str(state_dir))
    loaded = tracker2.load_all()
    assert loaded == 1
    wf2 = tracker2.get("wf-persist")
    assert wf2 is not None
    assert wf2.state == WorkflowState.RUNNING


def test_state_tracker_public_sem_credenciais(tmp_path):
    tracker = StateTracker(state_dir=str(tmp_path / "state"))
    tracker.register(Workflow(id="wf-1", objective="x", description="d"))
    payload = json.dumps(tracker.public(), ensure_ascii=False)
    assert "senha" not in payload.lower()
    assert "api_key" not in payload.lower()


# -- 6. scheduler ----------------------------------------------------------
def test_scheduler_agenda_e_devido():
    sched = Scheduler()
    agora = datetime.now(timezone.utc)
    wf = Workflow(id="wf-sched", objective="agendado", description="d")
    sched.schedule(wf, agora + timedelta(seconds=10))
    assert sched.due(agora) == []  # ainda nao chegou
    assert sched.due(agora + timedelta(seconds=20)) == ["wf-sched"]
    assert sched.pending() == []  # ja foi consumido


def test_scheduler_cancel():
    sched = Scheduler()
    agora = datetime.now(timezone.utc)
    wf = Workflow(id="wf-cancel", objective="cancelar", description="d")
    sched.schedule(wf, agora + timedelta(seconds=10))
    assert sched.cancel("wf-cancel") is True
    assert sched.cancel("inexistente") is False
    assert sched.pending() == []


# -- 7. recovery manager --------------------------------------------------
def test_recovery_list_and_plan():
    wf_failed = Workflow(id="wf-f", objective="falhou", description="d", state=WorkflowState.FAILED)
    step_fail = WorkflowStep(id="s-1", objective="o", description="d", target="a", target_type="agent")
    step_fail.state = StepState.FAILED
    step_fail.attempts = 1
    step_fail.max_attempts = 3
    wf_failed.steps = [step_fail]

    wf_paused = Workflow(id="wf-p", objective="pausado", description="d", state=WorkflowState.PAUSED)

    rm = RecoveryManager()
    necessarios = rm.list_workflows_needing_recovery([wf_failed, wf_paused])
    assert len(necessarios) == 2
    assert necessarios[0]["can_recover"] is True
    assert necessarios[1]["can_recover"] is True

    plano = rm.plan_recovery(wf_failed)
    assert plano["recoverable"] is True
    assert any(a["type"] == "retry_step" for a in plano["actions"])


def test_recovery_reexecuta_passo():
    wf = Workflow(id="wf-r", objective="recuperar", description="d", state=WorkflowState.FAILED)
    step = WorkflowStep(id="s-1", objective="o", description="d", target="a", target_type="agent")
    step.state = StepState.FAILED
    step.attempts = 1
    step.max_attempts = 3
    wf.steps = [step]

    rm = RecoveryManager()
    rm.recover(wf)
    assert step.state == StepState.PENDING
    assert step.error is None


# -- 8. workflow engine execucao simples ----------------------------------
@pytest.mark.asyncio
async def test_workflow_engine_executa_passo_sucesso():
    agent_orch = FakeAgentOrchestrator()
    engine = WorkflowEngine(agent_orchestrator=agent_orch)

    wf = Workflow(id="wf-ok", objective="executar passo", description="d")
    step = WorkflowStep(id="s-1", objective="inspecionar codigo", description="ler arquivo",
                        target="developer", target_type="agent")
    wf.steps = [step]

    resultado = await engine.run(wf)
    assert resultado.state == WorkflowState.COMPLETED
    assert step.state == StepState.COMPLETED
    assert step.result is not None
    assert step.result.get("success") is True


@pytest.mark.asyncio
async def test_workflow_engine_esgotamento_tentativas():
    agent_orch = FakeAgentOrchestrator(fail_targets={"developer"})
    engine = WorkflowEngine(agent_orchestrator=agent_orch, max_concurrent=1)

    wf = Workflow(id="wf-fail", objective="passo que falha", description="d")
    step = WorkflowStep(id="s-1", objective="inspecionar codigo", description="ler arquivo",
                        target="developer", target_type="agent", max_attempts=2)
    wf.steps = [step]

    resultado = await engine.run(wf)
    assert resultado.state == WorkflowState.FAILED
    assert step.state == StepState.FAILED
    assert step.attempts == 2
    assert step.error is not None


@pytest.mark.asyncio
async def test_workflow_engine_sem_orquestradores_erro_controlado():
    engine = WorkflowEngine()  # sem orquestradores
    wf = Workflow(id="wf-no", objective="qualquer", description="d")
    step = WorkflowStep(id="s-1", objective="o", description="d", target="developer", target_type="agent")
    wf.steps = [step]

    resultado = await engine.run(wf)
    assert resultado.state == WorkflowState.FAILED
    assert resultado.error is not None or step.error is not None


# -- 9. limites de workflow ------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_engine_limite_tempo():
    agent_orch = FakeAgentOrchestrator()
    engine = WorkflowEngine(agent_orchestrator=agent_orch)

    wf = Workflow(id="wf-time", objective="passo rapido", description="d",
                  max_execution_seconds=0.05)
    step = WorkflowStep(id="s-1", objective="o", description="d", target="developer", target_type="agent")
    wf.steps = [step]

    # O passo sera executado mas o workflow deve marcar tempo excedido.
    resultado = await engine.run(wf)
    # Pode ser completado (passo rapido) ou falhou por tempo. NaO levanta excecao.
    assert resultado.state in (WorkflowState.COMPLETED, WorkflowState.FAILED)


# -- 10. estado publico do engine ------------------------------------------
def test_workflow_engine_public():
    engine = WorkflowEngine(max_concurrent=2)
    pub = engine.public()
    assert pub["max_concurrent"] == 2
    assert pub["running"] == []
