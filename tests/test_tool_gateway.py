"""Teste E (ferramentas): descoberta, contratos, validação e execução.

O gateway valida parâmetros contra o contrato ANTES de executar, aplica
timeout em worker thread (o event loop nunca bloqueia) e audita. As
execuções reais usam apenas operações não destrutivas (system_status lê
métricas; um executor fake serve para timeout/erro).
"""

from __future__ import annotations

import asyncio

import ultron_2_0  # sys.path lain + Mark-LVI
from ultron_2_0.marklvi_actions import build_gateway
from ultron_2_0.tool_contracts import ToolContract


def test_descoberta_do_subset_curado():
    """Teste E.1: as 4 ferramentas aprovadas são descobertas e registradas."""
    gateway = build_gateway()
    assert gateway.names() == ["open_app", "reminder", "system_status", "web_search"]


def test_contratos_refletem_implementacao_real():
    """Teste E.2: campos obrigatórios, timeout e fonte refletem o TOOL real."""
    gateway = build_gateway()

    open_app = gateway.get_contract("open_app")
    assert open_app.required_fields == ["app_name"]
    assert open_app.source.endswith("actions/open_app.py")
    assert open_app.permissions == ["process:launch"]
    assert open_app.timeout_seconds == 20.0

    web_search = gateway.get_contract("web_search")
    assert web_search.required_fields == ["query"]
    assert "network:https" in web_search.permissions

    reminder = gateway.get_contract("reminder")
    assert reminder.required_fields == ["date", "time", "message"]

    system_status = gateway.get_contract("system_status")
    assert system_status.required_fields == []
    assert "system_monitor.py" in system_status.source


def test_validacao_ferramenta_desconhecida():
    gateway = build_gateway()
    result = asyncio.run(gateway.execute("nao_existe", {}))
    assert result.ok is False
    assert "unknown tool" in (result.error or "")
    assert "web_search" in (result.error or "")  # lista os disponíveis


def test_validacao_parametro_obrigatorio_ausente():
    gateway = build_gateway()
    result = asyncio.run(gateway.execute("web_search", {"mode": "search"}))
    assert result.ok is False
    assert "missing required parameter 'query'" in (result.error or "")


def test_validacao_parametro_desconhecido():
    gateway = build_gateway()
    result = asyncio.run(gateway.execute("web_search", {"query": "x", "zzz": 1}))
    assert result.ok is False
    assert "unknown parameter 'zzz'" in (result.error or "")


def test_validacao_tipo_incoercivel():
    gateway = build_gateway()
    result = asyncio.run(gateway.execute("web_search", {"query": 42}))
    assert result.ok is True  # int->str é coerção trivial: passa

    result = asyncio.run(gateway.execute("system_status", {"force": True}))
    assert result.ok is False
    assert "unknown parameter 'force'" in (result.error or "")


def test_coercao_string_para_numero_falha_limpa():
    from ultron_2_0.tool_gateway import _coerce

    try:
        _coerce("abc", "NUMBER")
        raise AssertionError("deveria ter levantado ValueError")
    except ValueError:
        pass
    assert _coerce("3", "NUMBER") == 3.0
    assert _coerce(7, "STRING") == "7"
    assert _coerce("true", "BOOLEAN") is True


async def test_execucao_real_system_status_nao_destrutiva():
    """Teste E.3: execução real (leituras de psutil) com resultado renderizado."""
    gateway = build_gateway()
    result = await gateway.execute("system_status", {})
    assert result.ok is True
    assert "cpu_percent" in str(result.result)
    rendered = result.render_for_model()
    assert rendered.startswith("status=done action=system_status")
    assert "cpu_percent" in rendered


async def test_timeout_e_teto_de_execucao():
    """Uma ferramenta que trava é abortada pelo timeout SEM derrubar o loop."""
    from ultron_2_0.tool_gateway import ToolGateway

    gateway = ToolGateway()

    def slow_executor(params: dict) -> str:
        import time

        time.sleep(5)
        return "nunca chega"

    gateway.register(
        ToolContract(
            name="slowpoke",
            description="trava de propósito",
            parameters={"type": "OBJECT", "properties": {}},
            timeout_seconds=0.2,
        ),
        slow_executor,
    )
    result = await gateway.execute("slowpoke", {})
    assert result.ok is False
    assert "timed out" in (result.error or "")


async def test_executor_que_explode_vira_resultado_de_falha():
    """Exceção da action não escapa do gateway (Teste G: recuperação)."""
    from ultron_2_0.tool_gateway import ToolGateway

    gateway = ToolGateway()

    def broken_executor(params: dict) -> str:
        raise RuntimeError("boom")

    gateway.register(
        ToolContract(name="broken", description="explode"),
        broken_executor,
    )
    result = await gateway.execute("broken", {})
    assert result.ok is False
    assert "RuntimeError" in (result.error or "")
    assert "boom" in (result.error or "")


async def test_ferramenta_com_confirmacao_e_recusada():
    """Contrato com requires_confirmation=True é recusado até o gate existir."""
    from ultron_2_0.tool_gateway import ToolGateway

    gateway = ToolGateway()
    gateway.register(
        ToolContract(
            name="dangerous",
            description="exigiria confirmação",
            requires_confirmation=True,
        ),
        lambda params: "nunca executa",
    )
    result = await gateway.execute("dangerous", {})
    assert result.ok is False
    assert "confirmation" in (result.error or "")
