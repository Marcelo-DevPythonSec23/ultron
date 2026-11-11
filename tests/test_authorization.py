"""Testes da autorização interativa (AGENTS.md 2.1, Fase 2).

Cobrem o contrato do `AuthorizationManager` e a integração real com o
`ToolGateway`: vínculo ferramenta+argumentos, token de uso único, expiração,
recusa, concorrência e o fluxo "o modelo propõe, a interface decide".
"""

from __future__ import annotations

import threading
import time

import pytest

from ultron_2_0.authorization import (
    ArgumentsMismatch,
    AuthorizationDenied,
    AuthorizationManager,
    ExpiredToken,
    PendingAction,
    TokenAlreadyUsed,
)
from ultron_2_0.tool_contracts import ToolContract
from ultron_2_0.tool_gateway import ToolGateway


class FakeClock:
    """Relógio injetável para testar expiração sem dormir."""

    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _gateway(
    manager: AuthorizationManager | None, *, auth_timeout: float = 5.0
) -> tuple[ToolGateway, list[dict]]:
    calls: list[dict] = []
    gateway = ToolGateway(authorization=manager)
    gateway.register(
        ToolContract(
            name="danger",
            description="ação destrutiva de teste",
            parameters={
                "type": "OBJECT",
                "properties": {"alvo": {"type": "STRING"}},
                "required": ["alvo"],
            },
            required_fields=["alvo"],
            requires_confirmation=True,
            timeout_seconds=5.0,
            authorization_timeout_seconds=auth_timeout,
        ),
        lambda params: calls.append(params) or "ok:destruído",
    )
    return gateway, calls


# -- contrato do manager ------------------------------------------------------


def test_pendencia_publica_nao_expoe_token():
    manager = AuthorizationManager()
    action = manager.request("forget", {"key": "cor"})
    public = manager.pending()[0]
    assert public["tool"] == "forget"
    assert public["arguments"] == {"key": "cor"}
    assert "token" not in public
    assert action.token not in str(public)


def test_aprovacao_consome_token_uma_unica_vez():
    manager = AuthorizationManager()
    action = manager.request("forget", {"key": "cor"})
    manager.approve(action.action_id)
    consumed = manager.consume(action.token, "forget", {"key": "cor"})
    assert consumed.status == "consumed"

    with pytest.raises(TokenAlreadyUsed):
        manager.consume(action.token, "forget", {"key": "cor"})


def test_argumentos_alterados_sao_rejeitados():
    manager = AuthorizationManager()
    action = manager.request("forget", {"key": "cor"})
    manager.approve(action.token)

    with pytest.raises(ArgumentsMismatch):
        manager.consume(action.token, "forget", {"key": "outra"})
    with pytest.raises(ArgumentsMismatch):
        manager.consume(action.token, "outra_ferramenta", {"key": "cor"})

    # O token não foi consumido por uma tentativa inválida.
    assert manager.consume(action.token, "forget", {"key": "cor"}).status == "consumed"


def test_token_expirado_nao_executa():
    clock = FakeClock()
    manager = AuthorizationManager(clock=clock, default_ttl_seconds=10)
    action = manager.request("forget", {"key": "cor"})
    clock.advance(11)

    with pytest.raises(ExpiredToken):
        manager.consume(action.token, "forget", {"key": "cor"})
    assert manager.pending() == []


def test_recusa_impede_consumo():
    manager = AuthorizationManager()
    action = manager.request("forget", {"key": "cor"})
    manager.reject(action.action_id, reason="não")

    with pytest.raises(AuthorizationDenied):
        manager.consume(action.token, "forget", {"key": "cor"})


def test_request_and_wait_com_handler_interativo():
    aprovado = AuthorizationManager(confirm_handler=lambda action: True)
    action = aprovado.request_and_wait("forget", {"key": "cor"})
    assert action.status == "consumed"

    recusado = AuthorizationManager(confirm_handler=lambda action: False)
    with pytest.raises(AuthorizationDenied):
        recusado.request_and_wait("forget", {"key": "cor"})


def test_request_and_wait_externo_aprova_de_outra_thread():
    manager = AuthorizationManager(default_ttl_seconds=10)
    result: dict[str, object] = {}

    def waiter() -> None:
        try:
            result["action"] = manager.request_and_wait("forget", {"key": "cor"})
        except Exception as exc:  # registra para a asserção abaixo
            result["error"] = exc

    thread = threading.Thread(target=waiter)
    thread.start()

    deadline = time.monotonic() + 5
    while not manager.pending() and time.monotonic() < deadline:
        time.sleep(0.01)
    action_id = manager.pending()[0]["action_id"]
    manager.approve(action_id)
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert "error" not in result
    assert result["action"].status == "consumed"


def test_consumo_concorrente_tem_um_vencedor():
    manager = AuthorizationManager()
    action = manager.request("forget", {"key": "cor"})
    manager.approve(action.action_id)

    outcomes: list[str] = []
    barrier = threading.Barrier(6)

    def consume() -> None:
        barrier.wait()
        try:
            manager.consume(action.token, "forget", {"key": "cor"})
            outcomes.append("ok")
        except TokenAlreadyUsed:
            outcomes.append("replay")

    threads = [threading.Thread(target=consume) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert outcomes.count("ok") == 1
    assert outcomes.count("replay") == 5


# -- integração com o gateway ------------------------------------------------


async def test_gateway_sem_manager_recusa_acao_sensivel():
    gateway, calls = _gateway(None)
    result = await gateway.execute("danger", {"alvo": "x"})
    assert result.ok is False
    assert result.metadata["authorization"] == "unavailable"
    assert calls == []


async def test_gateway_com_handler_aprova_e_executa():
    gateway, calls = _gateway(AuthorizationManager(confirm_handler=lambda action: True))
    result = await gateway.execute("danger", {"alvo": "x"})
    assert result.ok is True
    assert result.metadata["authorized"] is True
    assert calls == [{"alvo": "x"}]


async def test_gateway_com_handler_recusa_nao_executa():
    gateway, calls = _gateway(AuthorizationManager(confirm_handler=lambda action: False))
    result = await gateway.execute("danger", {"alvo": "x"})
    assert result.ok is False
    assert result.metadata["authorization"] == "denied"
    assert calls == []


async def test_gateway_exige_token_vinculado_aos_argumentos():
    manager = AuthorizationManager()
    gateway, calls = _gateway(manager)

    action = manager.request("danger", {"alvo": "x"})
    manager.approve(action.action_id)

    wrong = await gateway.execute("danger", {"alvo": "y"}, approval_token=action.token)
    assert wrong.ok is False
    assert wrong.metadata["reason"] == "ArgumentsMismatch"
    assert calls == []

    right = await gateway.execute("danger", {"alvo": "x"}, approval_token=action.token)
    assert right.ok is True
    assert calls == [{"alvo": "x"}]


async def test_gateway_timeout_de_autorizacao_nao_executa():
    manager = AuthorizationManager(default_ttl_seconds=0.05)
    gateway, calls = _gateway(manager, auth_timeout=0.05)
    result = await gateway.execute("danger", {"alvo": "x"})
    assert result.ok is False
    assert result.metadata["reason"] == "ExpiredToken"
    assert calls == []


def test_pending_action_tem_identificadores_distintos():
    manager = AuthorizationManager()
    first = manager.request("forget", {"key": "a"})
    second = manager.request("forget", {"key": "b"})
    assert isinstance(first, PendingAction)
    assert first.action_id != second.action_id
    assert first.token != second.token
    assert {item["action_id"] for item in manager.pending()} == {
        first.action_id,
        second.action_id,
    }
