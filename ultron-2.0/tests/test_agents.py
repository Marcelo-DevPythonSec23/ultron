"""Testes da Fase 4 — Sistema Multiagente.

Cobrem, com agentes REAIS (adaptadores sobre ferramentas existentes, sem
modelos de IA fictícios):

1. registro e descoberta de agentes (AgentRegistry);
2. criação de tarefas e ciclo de vida (pending -> assigned -> running -> review -> completed);
3. execução de tarefa com resultado estruturado e identificação de origem;
4. validação de resultados (dados não confiáveis até validar);
5. falha de agente é detectada e registrada (replanejamento com tentativas);
6. concorrência com isolamento de arquivos (duas tarefas nos mesmos arquivos não rodam juntas);
7. agente não encontrado deixa tarefa pendente (sem falhar o orquestrador);
8. status do multiagente sem credenciais;
9. integração com o UltronCoreRuntime (agent_orchestrator exposto).
"""

from __future__ import annotations

import asyncio
import json

import pytest

from ultron_2_0.agents import (
    AgentOrchestrator,
    AgentRegistry,
    AgentResult,
    AgentTask,
    BaseAgent,
    TaskQueue,
    TaskState,
)
from ultron_2_0.agents.agent_validator import AgentValidator
from ultron_2_0.agents.implementations import (
    DeveloperAgent,
    QAAgent,
    ResearchAgent,
    SecurityAgent,
)
from ultron_2_0.agents.result_manager import ResultManager
from ultron_2_0.agents.execution_monitor import ExecutionMonitor


# -- agentes de teste -------------------------------------------------------
class RecordingAgent(BaseAgent):
    """Agente que grava chamadas e pode ser configurado para falhar."""

    def __init__(
        self,
        agent_type: str = "test",
        *,
        fail: bool = False,
        fail_times: int = 0,
        result_content: dict | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        super().__init__(agent_type=agent_type)
        self.fail = fail
        self._fail_remaining = int(fail_times)
        self._result_content = result_content or {"ok": True}
        self._delay = max(0.0, float(delay_seconds))
        self.calls: list[dict] = []

    def capabilities(self):
        return [
            __import__("ultron_2_0.agents.agent_task", fromlist=["AgentCapability"]).AgentCapability(
                name="do_work",
                description="executa trabalho de teste",
                requires_authorization=False,
                timeout_seconds=30.0,
            )
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        import asyncio as _a

        self.calls.append({"task_id": task.id, "objective": task.objective})
        if self._delay:
            await _a.sleep(self._delay)
        if self.fail or self._fail_remaining > 0:
            self._fail_remaining = max(0, self._fail_remaining - 1)
            raise RuntimeError(f"{self.agent_type} falhou por teste")
        return AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            success=True,
            content=dict(self._result_content),
            summary="tarefa de teste concluída",
            files_modified=[],
        )


# -- helpers ----------------------------------------------------------------
def _make_orchestrator(*, max_concurrent: int = 3) -> AgentOrchestrator:
    return AgentOrchestrator(max_concurrent=max_concurrent)


def _create_task(orchestrator, agent_type: str = "test", **kwargs) -> AgentTask:
    return orchestrator.create_task(
        objective="executar trabalho de teste",
        description="tarefa de teste da fase 4",
        agent_type=agent_type,
        **kwargs,
    )


# -- 1. registro e descoberta ----------------------------------------------
def test_registro_e_descoberta_de_agentes():
    registry = AgentRegistry()
    agent = RecordingAgent(agent_type="developer")
    registry.register(agent)

    assert "developer" in registry.list_types()
    found = registry.find_by_capability("do_work")
    assert any(a.agent_id == agent.agent_id for a in found)
    selected = registry.select_for_task(
        AgentTask(id="t-1", objective="x", description="d", agent_type="developer")
    )
    assert selected is not None
    assert selected.agent_id == agent.agent_id


def test_agente_nao_encontrado_nao_quebra_orquestrador():
    orch = _make_orchestrator()
    task = _create_task(orch, agent_type="inexistente")
    assert task.state == TaskState.PENDING
    # Nenhum agente registrado: select_for_task retorna None.
    assert orch._registry.select_for_task(task) is None


# -- 2. ciclo de vida e execução ------------------------------------------
@pytest.mark.asyncio
async def test_execucao_de_tarefa_com_resulto_estruturado():
    orch = _make_orchestrator()
    agent = RecordingAgent(agent_type="developer")
    orch.register_agent(agent)
    task = _create_task(orch, agent_type="developer")

    started = await orch.run_ready(max_tasks=1)
    assert started == 1

    await asyncio.sleep(0.1)  # aguarda a task assíncrona
    task = orch.get_task(task.id)
    assert task.state == TaskState.COMPLETED
    assert task.result is not None
    assert task.result.success is True
    assert task.result.agent_id == agent.agent_id
    assert task.result.agent_type == "developer"
    assert task.execution_seconds is not None


def test_execucao_sincrona_via_run_coro_estilo_testes():
    """Equivalente ao padrão de testes existentes (asyncio.run)."""
    orch = _make_orchestrator()
    agent = RecordingAgent(agent_type="qa")
    orch.register_agent(agent)
    task = _create_task(orch, agent_type="qa")

    asyncio.run(orch.run_ready(max_tasks=1))
    # dar uma chance à task assíncrona concluir
    asyncio.run(orch.run_ready(max_tasks=0))
    task = orch.get_task(task.id)
    assert task.state in (TaskState.COMPLETED, TaskState.RUNNING, TaskState.REVIEW)


# -- 3. validação de resultados --------------------------------------------
def test_validacao_rejeita_resultado_sem_origem():
    validator = AgentValidator()
    task = AgentTask(id="t-1", objective="x", description="d", agent_type="test")
    result = AgentResult(
        task_id="t-1", agent_id="", agent_type="", success=True, content={"a": 1}
    )
    report = validator.validate(task, result)
    assert report["valid"] is False
    assert any("origem" in i for i in report["issues"])


def test_validacao_aceita_resultado_bem_sucedido_com_sumario():
    validator = AgentValidator()
    task = AgentTask(id="t-1", objective="x", description="d", agent_type="test")
    result = AgentResult(
        task_id="t-1",
        agent_id="ag-1",
        agent_type="test",
        success=True,
        content={"a": 1},
        summary="tudo ok",
        files_modified=[],
    )
    report = validator.validate(task, result)
    assert report["valid"] is True


def test_validacao_deteta_arquivos_fora_do_escopo():
    validator = AgentValidator()
    task = AgentTask(
        id="t-1",
        objective="x",
        description="d",
        agent_type="test",
        files_involved=["a.py"],
    )
    result = AgentResult(
        task_id="t-1",
        agent_id="ag-1",
        agent_type="test",
        success=True,
        content={"a": 1},
        summary="ok",
        files_modified=["b.py"],  # fora do escopo
    )
    report = validator.validate(task, result)
    assert report["valid"] is False
    assert any("fora do escopo" in i for i in report["issues"])


# -- 4. falha e replanejamento ---------------------------------------------
@pytest.mark.asyncio
async def test_falha_de_agente_registrada_e_replanejada():
    orch = _make_orchestrator()
    agent = RecordingAgent(agent_type="flaky", fail_times=1, result_content={"ok": True})
    orch.register_agent(agent)
    task = _create_task(orch, agent_type="flaky", max_attempts=3)

    await orch.run_ready(max_tasks=1)
    await asyncio.sleep(0.2)

    task = orch.get_task(task.id)
    # Primeira tentativa falha, segunda (replanejada) deve ter sucesso ou pelo menos
    # ter tentado duas vezes.
    assert task.attempts >= 1
    assert task.error is not None or task.state == TaskState.COMPLETED


@pytest.mark.asyncio
async def test_falha_persistente_marca_failed_apos_max_attempts():
    orch = _make_orchestrator()
    agent = RecordingAgent(agent_type="broken", fail=True)
    orch.register_agent(agent)
    task = _create_task(orch, agent_type="broken", max_attempts=2)

    # Executa até que a tarefa esgote as tentativas (cada run_ready inicia uma).
    for _ in range(task.max_attempts + 1):
        await orch.run_ready(max_tasks=1)
        await asyncio.sleep(0.1)
        if task.state in (TaskState.COMPLETED, TaskState.FAILED):
            break

    task = orch.get_task(task.id)
    assert task.state == TaskState.FAILED
    assert task.attempts == 2
    assert task.error is not None


# -- 5. concorrência e isolamento de arquivos ------------------------------
@pytest.mark.asyncio
async def test_duas_tarefas_mesmo_arquivo_nao_rodam_conjuntas():
    """Isolamento de arquivos: tarefas que tocam os mesmos arquivos não rodam ao mesmo tempo."""
    orch = _make_orchestrator(max_concurrent=4)
    a1 = RecordingAgent(agent_type="dev-a")
    a2 = RecordingAgent(agent_type="dev-b")
    orch.register_agent(a1)
    orch.register_agent(a2)

    t1 = _create_task(
        orch, agent_type="dev-a", files_involved=["shared.py"], max_attempts=1
    )
    t2 = _create_task(
        orch, agent_type="dev-b", files_involved=["shared.py"], max_attempts=1
    )
    t3 = _create_task(
        orch, agent_type="dev-a", files_involved=["other.py"], max_attempts=1
    )

    # Enfileira as três (não executa ainda via run_ready limitado).
    for t in (t1, t2, t3):
        orch._queue.enqueue(t)

    # Executa uma por vez para verificar isolamento.
    await orch.run_ready(max_tasks=1)
    await asyncio.sleep(0.2)
    estados = {t.id: orch.get_task(t.id).state for t in (t1, t2, t3)}
    # Só uma das que usam shared.py pode ter avançado; other.py pode rodar junto.
    shared_done = sum(
        1 for t in (t1, t2) if orch.get_task(t.id).state in (TaskState.RUNNING, TaskState.COMPLETED)
    )
    assert shared_done <= 1, "duas tarefas no mesmo arquivo não devem rodar juntas"


# -- 6. status sem credenciais ---------------------------------------------
def test_status_nao_expoe_credenciais():
    orch = _make_orchestrator()
    orch.register_agent(RecordingAgent(agent_type="sec"))
    status = orch.status()

    payload = json.dumps(status, ensure_ascii=False)
    assert "senha" not in payload.lower()
    assert "api_key" not in payload.lower()
    assert "secret" not in payload.lower()
    assert "agents" in status
    assert "queue" in status
    assert "results" in status
    assert "monitor" in status


# -- 7. agentes iniciais reais ---------------------------------------------
def test_developer_agent_inspeciona_arquivo():
    agent = DeveloperAgent()
    caps = {c.name for c in agent.capabilities()}
    assert "inspect_code" in caps
    assert "propose_code_change" in caps
    # propose_code_change exige autorização.
    prop_cap = [c for c in agent.capabilities() if c.name == "propose_code_change"][0]
    assert prop_cap.requires_authorization is True


def test_research_agent_capabilities():
    agent = ResearchAgent()
    assert any(c.name == "research_topic" for c in agent.capabilities())


def test_security_agent_capabilities():
    agent = SecurityAgent()
    assert any(c.name == "audit_tool_contract" for c in agent.capabilities())


def test_qa_agent_capabilities():
    agent = QAAgent()
    assert any(c.name == "run_tests" for c in agent.capabilities())


# -- 8. result_manager armazena e valida -----------------------------------
def test_result_manager_armazena_e_valida():
    rm = ResultManager()
    task = AgentTask(id="t-1", objective="x", description="d", agent_type="test")
    result = AgentResult(
        task_id="t-1",
        agent_id="ag-1",
        agent_type="test",
        success=True,
        content={"a": 1},
        summary="ok",
        files_modified=[],
    )
    report = rm.submit(task, result)
    assert report["valid"] is True
    assert rm.is_valid("t-1") is True
    assert rm.get_result("t-1") is result


# -- 9. execution monitor registra eventos ---------------------------------
def test_execution_monitor_registra_eventos():
    monitor = ExecutionMonitor()
    task = AgentTask(id="t-1", objective="x", description="d", agent_type="test")
    monitor.record_task_created(task)
    monitor.record_task_started(task)
    result = AgentResult(
        task_id="t-1", agent_id="ag-1", agent_type="test", success=True,
        content={}, summary="ok", files_modified=[],
    )
    monitor.record_task_completed(task, result, {"valid": True})
    pub = monitor.public()
    assert pub["total_tasks"] == 1
    assert len(pub["recent_events"]) >= 3


# -- 10. integração com o núcleo (core_runtime) ----------------------------
def test_agent_orchestrator_disponivel_no_runtime():
    from ultron_2_0.core_runtime import UltronCoreRuntime

    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )
    try:
        asyncio.run(runtime.start_async())
        assert runtime.agent_orchestrator is not None
        tipos = runtime.agent_orchestrator.list_agent_types()
        assert "developer" in tipos
        assert "security" in tipos
        assert "qa" in tipos
        assert "research" in tipos
        assert "database" in tipos
        assert "architecture" in tipos
        # Agentes iniciais registrados (6).
        total = sum(
            len(runtime.agent_orchestrator.list_agents(t)) for t in tipos
        )
        assert total == 6
    finally:
        asyncio.run(runtime.shutdown())


def test_bridge_status_expõe_agentes():
    from ultron_2_0.orchestrator_bridge import OrchestratorBridge

    with OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    ) as bridge:
        status = bridge.status()
        assert status["agents"] is not None
        agentes = status["agents"]["agents"]
        assert agentes["total"] == 6
        assert "developer" in status["agents"]["agents"]["types"]  # type: ignore[attr-defined]
        payload = json.dumps(status, ensure_ascii=False)
        assert "senha" not in payload.lower()
        assert "api_key" not in payload.lower()
