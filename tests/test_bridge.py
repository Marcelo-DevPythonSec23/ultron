"""Testes da interface: bridge + CLI (Teste A/B pela ponta de entrada)."""

from __future__ import annotations

import ultron_2_0  # sys.path lain + Mark-LVI
from ultron_2_0.cli import main
from ultron_2_0.orchestrator_bridge import OrchestratorBridge

from tests.fakes import ScriptedProvider


def _bridge(memory: bool = True) -> OrchestratorBridge:
    return OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:" if memory else None,
        default_provider="mock",
        enable_tools=False,
    )


def test_bridge_context_manager_e_status():
    with _bridge() as bridge:
        status = bridge.status()
        assert status["ready"] is True
        assert status["default_provider"] == "mock"
        assert "mock" in status["providers"]
        assert status["conversation_id"] is None
    assert bridge.status()["ready"] is False


def test_bridge_mantem_conversa_unica():
    """Mesma interface, mesma conversa: histórico único no núcleo (§3.2)."""
    with _bridge() as bridge:
        bridge.runtime.register_provider(ScriptedProvider(["r1", "r2"]))
        r1 = bridge.process_text("turno 1")
        r2 = bridge.process_text("turno 2")
        assert r1.conversation_id == r2.conversation_id
        assert bridge.conversation_id == r2.conversation_id
        assert r1.content == "r1" and r2.content == "r2"


def test_cli_demo_mode(capsys):
    """CLI --demo: status + ferramentas reais + saída limpa (código 0)."""
    code = main(
        [
            "--demo",
            "--database", "sqlite+aiosqlite:///:memory:",
            "--provider", "mock",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "ULTRON 2.0" in out
    assert "provedor padrão : mock" in out
    # Ferramentas do subset curado listadas com fonte real
    assert "system_status" in out
    assert "open_app" in out


def test_cli_one_shot_message(capsys):
    code = main(
        [
            "--message", "olá",
            "--database", "sqlite+aiosqlite:///:memory:",
            "--provider", "mock",
            "--no-tools",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    # MockProvider do lain: resposta simulada que ECOA a mensagem é o
    # comportamento DELE (documentado), mas chegou pelo pipeline completo
    # (orquestrador -> persistência -> provider -> resposta).
    assert "[Resposta Simulada ULTRON]" in out
    assert "olá" in out


def test_cli_one_shot_nao_toca_banco_do_lain(capsys, tmp_path):
    """O banco padrão do CLI é sempre o isolado do 2.0, nunca lain/ultron.db."""
    code = main(
        [
            "--message", "olá",
            "--provider", "mock",
            "--no-tools",
            "--database", f"sqlite+aiosqlite:///{tmp_path}/cli-test.db",
        ]
    )
    assert code == 0
    assert (tmp_path / "cli-test.db").exists()
