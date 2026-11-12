"""Testes da Fase 5 — Integração com Agentes CLI e MCP.

Cobrem, sem exigir chave de API nem servidor MCP real:

1. OpenCodeAdapter.build_command monta o comando real do OpenCode.
2. OpenCodeAdapter.parse_output parseia saída JSON e texto bruto.
3. Sanitização de segredos na saída de processo externo.
4. Integração desabilitada não executa (erro controlado).
5. Comando não encontrado trata erro sem derrubar o núcleo.
6. Timeout trata erro controlado.
7. IntegrationRegistry: registro, listar, habilitar/desabilitar individual.
8. IntegrationOrchestrator: cria tarefa, executa, integração não registrada.
9. Status sem expor credenciais.
10. Integração MCP lista servidores via `opencode mcp list`.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from ultron_2_0.integrations import (
    IntegrationOrchestrator,
    IntegrationRegistry,
    IntegrationState,
    IntegrationTask,
    IntegrationType,
    MCPAdapter,
    OpenCodeAdapter,
)
from ultron_2_0.integrations.contracts import new_task_id
from ultron_2_0.integrations.base import sanitize_output


# -- adaptadores --------------------------------------------------------------
def _opencode_adapter(**kwargs) -> OpenCodeAdapter:
    return OpenCodeAdapter(timeout_seconds=5.0, **kwargs)


def _mcp_adapter(**kwargs) -> MCPAdapter:
    return MCPAdapter(timeout_seconds=5.0, **kwargs)


# -- 1. build_command --------------------------------------------------------
def test_opencode_build_command_monta_comando_real():
    adapter = _opencode_adapter(default_session="sess-1", default_model="provider/model")
    task = IntegrationTask(
        id=new_task_id(),
        integration_type=IntegrationType.CLI,
        target="opencode",
        prompt="explique o codigo",
        params={"session": "sess-2"},
    )
    cmd = adapter.build_command(task)
    assert cmd[0] == "opencode"
    assert cmd[1] == "run"
    assert "--format" in cmd and "json" in cmd
    assert "--session" in cmd and "sess-2" in cmd  # params vencem default
    assert "--model" in cmd and "provider/model" in cmd
    assert task.prompt in cmd
    assert "--auto" not in cmd


def test_opencode_build_command_auto_approve():
    adapter = _opencode_adapter(auto_approve=True)
    task = IntegrationTask(
        id=new_task_id(),
        integration_type=IntegrationType.CLI,
        target="opencode",
        prompt="oi",
    )
    cmd = adapter.build_command(task)
    assert "--auto" in cmd


# -- 2. parse_output ---------------------------------------------------------
def test_opencode_parse_output_json():
    adapter = _opencode_adapter()
    out = json.dumps({"summary": "resultado do opencode", "text": "texto completo"})
    parsed = adapter.parse_output(out)
    assert parsed["summary"] == "resultado do opencode"
    assert parsed["text"] == "texto completo"


def test_opencode_parse_output_texto_bruto():
    adapter = _opencode_adapter()
    parsed = adapter.parse_output("qualquer texto nao json")
    assert parsed["summary"] == "qualquer texto nao json"
    assert parsed["text"] == "qualquer texto nao json"


def test_opencode_parse_output_vazio():
    adapter = _opencode_adapter()
    assert adapter.parse_output("")["summary"] == "saída vazia do OpenCode"


# -- 3. sanitizacao de segredos ---------------------------------------------
def test_sanitize_output_remove_chaves():
    assert "AIza" not in sanitize_output("chave AIzaSyABCDEFGHIJKLMNOPQRSTUV123456")
    assert "sk-" not in sanitize_output("token sk-abcdefghijklmno")
    assert "[redacted]" in sanitize_output("API_KEY=valor-secreto")
    assert sanitize_output(None) is None
    # string longa sem espaco eh tratada como possivel token e reduzida
    longo = sanitize_output("x" * 5000)
    assert len(longo) <= 2000
    assert "x" * 5000 not in longo
    # string com espacos (nao e token) eh apenas truncada
    truncado = sanitize_output("a " * 3000)
    assert len(truncado) <= 2000


def test_opencode_sanitiza_saida_com_segredo():
    adapter = _opencode_adapter()
    out = json.dumps({"summary": "chave AIzaSyABCDEFGHIJKLMNOPQRSTUV123456 vazou"})
    parsed = adapter.parse_output(out)
    assert "AIza" not in parsed["summary"]
    assert "[redacted]" in parsed["summary"]


# -- 4. integracao desabilitada ---------------------------------------------
def test_integracao_desabilitada_nao_executa():
    adapter = _opencode_adapter(enabled=False)
    task = IntegrationTask(
        id=new_task_id(),
        integration_type=IntegrationType.CLI,
        target="opencode",
        prompt="oi",
    )
    result = asyncio.run(adapter.run(task))
    assert result.success is False
    assert "desabilitada" in (result.error or "")


# -- 5. comando nao encontrado ----------------------------------------------
def test_comando_nao_encontrado_erro_controlado():
    adapter = OpenCodeAdapter(opencode_cmd="comando-inexistente-opencode", timeout_seconds=2.0)
    task = IntegrationTask(
        id=new_task_id(),
        integration_type=IntegrationType.CLI,
        target="opencode",
        prompt="oi",
    )
    result = asyncio.run(adapter.run(task))
    assert result.success is False
    assert "não encontrado" in result.error or "no such file" in result.error.lower()


# -- 6. timeout --------------------------------------------------------------
@pytest.mark.asyncio
async def test_timeout_tratado_controlado():
    adapter = OpenCodeAdapter(opencode_cmd="sleep", timeout_seconds=0.05)
    adapter.build_command = lambda t: ["sleep", "10"]
    task = IntegrationTask(
        id=new_task_id(),
        integration_type=IntegrationType.CLI,
        target="opencode",
        prompt="oi",
    )
    result = await adapter.run(task)
    assert result.success is False
    assert "timeout" in (result.error or "")


# -- 7. registro -------------------------------------------------------------
def test_registro_habilitar_deshabilitar_integracao():
    registry = IntegrationRegistry()
    adapter = _opencode_adapter()
    registry.register(adapter)

    assert registry.get("opencode") is adapter
    assert "opencode" in registry.list_targets()
    assert registry.is_enabled("opencode") is True

    assert registry.disable("opencode") is True
    assert registry.is_enabled("opencode") is False

    assert registry.enable("opencode") is True
    assert registry.is_enabled("opencode") is True

    assert registry.unregister("opencode") is True
    assert registry.get("opencode") is None


def test_registro_publico_sem_credenciais():
    registry = IntegrationRegistry()
    registry.register(_opencode_adapter())
    registry.register(_mcp_adapter())
    payload = json.dumps(registry.public(), ensure_ascii=False)
    assert "AIza" not in payload
    assert "sk-" not in payload
    assert "senha" not in payload.lower()
    assert "api_key" not in payload.lower()


# -- 8. orquestrador ---------------------------------------------------------
def test_orquestrador_cria_tarefa():
    orch = IntegrationOrchestrator()
    task = orch.create_task(
        integration_type=IntegrationType.CLI,
        target="opencode",
        prompt="analise este codigo",
    )
    assert task.id is not None
    assert task.state == IntegrationState.PENDING
    assert orch.get_task(task.id) is task


def test_orquestrador_integracao_nao_registrada():
    orch = IntegrationOrchestrator()
    task = orch.create_task(
        integration_type=IntegrationType.CLI,
        target="inexistente",
        prompt="oi",
    )
    result = asyncio.run(orch.run_task(task))
    assert result.success is False
    assert "não registrada" in result.error


def test_orquestrador_integracao_desabilitada():
    orch = IntegrationOrchestrator()
    orch.register_integration(_opencode_adapter(enabled=False))
    task = orch.create_task(
        integration_type=IntegrationType.CLI,
        target="opencode",
        prompt="oi",
    )
    result = asyncio.run(orch.run_task(task))
    assert result.success is False
    assert "desabilitada" in (result.error or "")


def test_orquestrador_status_sem_credenciais():
    orch = IntegrationOrchestrator()
    orch.register_integration(_opencode_adapter())
    status = orch.status()
    payload = json.dumps(status, ensure_ascii=False)
    assert "AIza" not in payload
    assert "api_key" not in payload.lower()
    assert "integrations" in status
    assert "tasks" in status


# -- 9. mcp ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_mcp_adapter_lista_servidores():
    # Sem servidor MCP real, `opencode mcp list` deve falhar (comando existe
    # mas sem configuracao) ou retornar lista vazia. Teste nao exige servidor.
    adapter = _mcp_adapter()
    task = IntegrationTask(
        id=new_task_id(),
        integration_type=IntegrationType.MCP,
        target="mcp",
        prompt="listar",
    )
    result = await adapter.run(task)
    # Pode ser sucesso (lista vazia) ou falha (comando nao encontrado/config).
    # O importante: nao levanta excecao nao tratada.
    assert result is not None
    assert isinstance(result.success, bool)


# -- 10. integracao com o nucleo (core_runtime) ------------------------------
def test_integration_orchestrator_disponivel_no_runtime():
    from ultron_2_0.core_runtime import UltronCoreRuntime

    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )
    try:
        asyncio.run(runtime.start_async())
        assert runtime.integration_orchestrator is not None
        alvos = list(
            runtime.integration_orchestrator.list_integrations()[
                "integrations"
            ].keys()
        )
        assert "opencode" in alvos
        assert "mcp" in alvos
    finally:
        asyncio.run(runtime.shutdown())


def test_bridge_status_expõe_integracao():
    from ultron_2_0.orchestrator_bridge import OrchestratorBridge

    with OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    ) as bridge:
        status = bridge.status()
        assert status["integrations"] is not None
        integ = status["integrations"]["integrations"]["integrations"]
        assert "opencode" in integ
        assert "mcp" in integ
        payload = json.dumps(status, ensure_ascii=False)
        assert "senha" not in payload.lower()
        assert "api_key" not in payload.lower()


# -- helper ------------------------------------------------------------------
class ExternalIntegrationStub:
    """Stub para forçar comando arbitrável no teste de timeout."""

    def __init__(self, command: str, timeout_seconds: float):
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.enabled = True
        self.integration_type = IntegrationType.CLI
        self.target = "stub"

    def is_enabled(self):
        return self.enabled

    def build_command(self, task):
        return [self.command]

    def parse_output(self, stdout):
        return {"summary": stdout[:100]}
