"""Testes do HUD web (Etapa 5).

O HUD é uma PONTA de entrada, não um segundo cérebro: estes testes provam que
todo estado exibido vem do núcleo real, que `/api/chat` passa pelo MESMO
orquestrador do lain (histórico único) e que uma falha de provedor vira um erro
HTTP controlado — nunca um estado simulado.
"""

from __future__ import annotations

import ultron_2_0  # sys.path lain + Mark-LVI
import pytest
from fastapi.testclient import TestClient

from app.intelligence.providers.base import LLMProvider
from app.models.message import LLMRequest
from tests.fakes import ScriptedProvider
from ultron_2_0.orchestrator_bridge import OrchestratorBridge
from ultron_2_0.web.app import create_app, tool_calls_summary
from ultron_2_0.web.server import _parser

TOOLS_ESPERADAS = {
    "system_status",
    "open_app",
    "web_search",
    "reminder",
    "remember",
    "recall",
    "forget",
}


class _FailingProvider(LLMProvider):
    """Provedor que sempre falha — para exercitar o erro controlado do HUD."""

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "failing-model"

    async def generate_response(self, request: LLMRequest):
        raise RuntimeError("provider indisponível (teste)")

    async def generate_stream(self, request: LLMRequest):
        raise RuntimeError("provider indisponível (teste)")
        yield ""  # pragma: no cover

    async def health_check(self) -> bool:
        return False


def _audio() -> dict:
    return {"microphone": "teste-mic", "speaker": "teste-speaker"}


@pytest.fixture()
def client():
    """Bridge real (banco em memória) + app FastAPI, encerrados no fim."""
    with OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=True,
    ) as bridge:
        with TestClient(create_app(bridge, audio_probe=_audio)) as test_client:
            yield test_client, bridge


def test_hud_serve_html_com_tokens_de_identidade(client):
    _, _bridge = client
    response = _bridge  # noqa: F841 — legibilidade
    html = client[0].get("/").text
    assert "<title>ULTRON 2.0</title>" in html
    # Cores centralizadas em tokens (§10), não espalhadas.
    assert "--red-bright" in html
    assert "fetch(" in html  # a interface conversa com a API real
    assert "cdn" not in html.lower()  # nenhuma dependência externa


def test_status_reflete_o_nucleo_real(client):
    test_client, bridge = client
    body = test_client.get("/api/status").json()

    assert body["ready"] is True
    assert body["default_provider"] == "mock"
    assert "mock" in body["providers"]
    assert body["conversation_id"] is None
    assert body["database"].startswith("sqlite://")
    assert body["memory"]  # memória explícita do 2.0 está ligada
    assert body["audio"] == {"microphone": "teste-mic", "speaker": "teste-speaker"}
    assert body["web_uptime_seconds"] >= 0
    # O núcleo aponta para a raiz que contém os projetos originais.
    assert (bridge.runtime.project_root / "lain").is_dir()


def test_status_sobrevive_a_falha_do_probe_de_audio():
    with OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    ) as bridge:
        def boom():
            raise OSError("sem dispositivo de áudio")

        with TestClient(create_app(bridge, audio_probe=boom)) as test_client:
            body = test_client.get("/api/status").json()
    assert "error" in body["audio"]
    assert "sem dispositivo" in body["audio"]["error"]


def test_tools_lista_o_subset_real_e_a_memoria(client):
    test_client, _bridge = client
    tools = test_client.get("/api/tools").json()["tools"]
    names = {tool["name"] for tool in tools}
    assert names == TOOLS_ESPERADAS

    by_name = {tool["name"]: tool for tool in tools}
    # Contratos vêm da implementação real, não de uma lista decorativa.
    assert by_name["open_app"]["source"]
    assert by_name["forget"]["requires_confirmation"] is True
    assert "memory:read" in by_name["recall"]["permissions"]
    assert by_name["remember"]["required"] == ["key", "value"]


def test_chat_persiste_no_historico_do_nucleo(client):
    test_client, bridge = client
    bridge.runtime.register_provider(ScriptedProvider(["olá do provedor"]))

    response = test_client.post("/api/chat", json={"message": "oi ultrón"})
    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "olá do provedor"
    assert body["conversation_id"]
    assert body["provider"] == "mock"
    assert body["usage"]["total_tokens"] == 2
    assert body["tool_calls"] == []

    # A conversa corrente do bridge é a MESMA do núcleo.
    assert bridge.conversation_id == body["conversation_id"]

    history = test_client.get("/api/history").json()
    assert history["conversation_id"] == body["conversation_id"]
    roles = [message["role"] for message in history["messages"]]
    assert roles == ["user", "assistant"]
    assert history["messages"][0]["content"] == "oi ultrón"
    assert history["messages"][1]["content"] == "olá do provedor"


def test_chat_encadeia_a_mesma_conversa(client):
    test_client, bridge = client
    bridge.runtime.register_provider(ScriptedProvider(["r1", "r2"]))

    first = test_client.post("/api/chat", json={"message": "turno 1"}).json()
    second = test_client.post("/api/chat", json={"message": "turno 2"}).json()

    assert first["conversation_id"] == second["conversation_id"]
    messages = test_client.get("/api/history").json()["messages"]
    assert len(messages) == 4


def test_new_encerra_a_conversa_sem_apagar_o_historico(client):
    test_client, bridge = client
    bridge.runtime.register_provider(ScriptedProvider(["resposta"]))
    first = test_client.post("/api/chat", json={"message": "antes"}).json()

    reset = test_client.post("/api/new").json()
    assert reset == {"conversation_id": None, "status": "new-conversation"}
    assert bridge.conversation_id is None
    assert test_client.get("/api/history").json()["messages"] == []

    second = test_client.post("/api/chat", json={"message": "depois"}).json()
    assert second["conversation_id"] != first["conversation_id"]


def test_falha_de_provedor_vira_502_controlado(client):
    test_client, bridge = client
    bridge.runtime.register_provider(_FailingProvider())

    response = test_client.post("/api/chat", json={"message": "quebre"})
    assert response.status_code == 502
    assert "provider indisponível" in response.json()["detail"]

    # O HUD continua de pé e o status segue legível.
    assert test_client.get("/api/status").json()["ready"] is True


def test_mensagem_vazia_e_rejeitada_pelo_contrato(client):
    test_client, _bridge = client
    response = test_client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


def test_tool_calls_summary_tolera_metadata_invalido():
    assert tool_calls_summary(None) == []
    assert tool_calls_summary("não-json") == []
    assert tool_calls_summary('{"tool_calls": [{"tool": "recall", "ok": true}]}') == [
        {"tool": "recall", "ok": True}
    ]


def test_servidor_escuta_local_por_padrao():
    args = _parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.open is False


# -- autorização interativa pelo HUD (Fase 2 do ULTRON 2.1) -------------------


def test_hud_lista_aprova_e_libera_a_acao(client):
    test_client, bridge = client
    manager = bridge.runtime.authorization
    action = manager.request("forget", {"key": "cor"})

    body = test_client.get("/api/approvals").json()
    assert [item["action_id"] for item in body["pending"]] == [action.action_id]
    assert "token" not in body["pending"][0]
    assert test_client.get("/api/status").json()["pending_approvals"] == 1

    approved = test_client.post(f"/api/approvals/{action.action_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["action"]["status"] == "approved"

    assert test_client.get("/api/approvals").json()["pending"] == []
    assert manager.consume(action.token, "forget", {"key": "cor"}).status == "consumed"


def test_hud_recusa_e_rejeita_replay_e_id_desconhecido(client):
    test_client, bridge = client
    manager = bridge.runtime.authorization
    action = manager.request("forget", {"key": "cor"})

    rejected = test_client.post(
        f"/api/approvals/{action.action_id}/reject", json={"reason": "não"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["action"]["status"] == "rejected"

    replay = test_client.post(f"/api/approvals/{action.action_id}/approve")
    assert replay.status_code == 409

    unknown = test_client.post("/api/approvals/inexistente/approve")
    assert unknown.status_code == 404

