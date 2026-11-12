"""Teste A (inicialização) + Teste B (conversação por texto) do núcleo.

O núcleo é o ORQUESTRADOR ORIGINAL do lain, montado pelo UltronCoreRuntime —
banco em memória (nunca lain/ultron.db), provedor scriptável no lugar do mock.
Valida: boot/wiring, persistência entre turnos, recuperação de contexto,
ponte síncrona (loop dedicado em thread de background) e idempotência.
"""

from __future__ import annotations

from ultron_2_0.core_runtime import UltronCoreRuntime
from ultron_2_0.orchestrator_bridge import OrchestratorBridge

from tests.fakes import ScriptedProvider


async def test_boot_do_nucleo():
    """Teste A: núcleo sobe com banco em memória e providers registrados."""
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )
    try:
        await runtime.start_async()
        assert runtime.orchestrator is not None
        assert runtime.registry.default_provider_id == "mock"
        assert "mock" in runtime.registry.list_providers()
        # A chave real do lain/.env existe neste ambiente: gemini é registrado
        # (construção do cliente não faz rede). Em ambiente sem chave, fica só
        # o mock — o teste aceita os dois estados reais.
        if runtime.settings.get_gemini_api_key():
            assert "gemini" in runtime.registry.list_providers()
        assert runtime.gateway is None  # enable_tools=False
    finally:
        await runtime.shutdown()
    assert runtime.orchestrator is None


async def test_start_e_idempotente():
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )
    try:
        first = await runtime.start_async()
        second = await runtime.start_async()
        assert first is runtime and second is runtime
    finally:
        await runtime.shutdown()


async def test_conversa_texto_ponta_a_ponta():
    """Teste B: turno completo — persistência, contexto e resposta final."""
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )
    try:
        await runtime.start_async()
        scripted = ScriptedProvider(["primeira resposta", "segunda resposta"])
        runtime.register_provider(scripted)  # substitui "mock" no registry

        r1 = await runtime.chat("olá, ULTRON")
        # Contrato do orquestrador do lain (mesmo da API REST dele):
        # conversation_id=None abre conversa NOVA a cada turno. Quem mantém a
        # sessão é a interface — o bridge repassa o id capturado. Aqui
        # modelamos exatamente isso.
        r2 = await runtime.chat("continuando", conversation_id=r1.conversation_id)

        # Respostas vêm do provedor (não de eco, não de fallback)
        assert r1.content == "primeira resposta"
        assert r2.content == "segunda resposta"

        # Mesma conversa persistida pelo núcleo (histórico único)
        assert r1.conversation_id == r2.conversation_id

        # O 2º turno carregou o 1º do BANCO (contexto real, não em memória
        # de interface): a requisição ao modelo contém o intercâmbio anterior.
        second_call_messages = [m.content for m in scripted.calls[1].messages]
        assert "olá, ULTRON" in second_call_messages
        assert "primeira resposta" in second_call_messages
        assert "continuando" in second_call_messages

        # Persistência com uso registrado
        assert r2.usage.total_tokens >= 2
        assert r2.message_id
    finally:
        await runtime.shutdown()


def test_ponte_sincrona_com_loop_dedicado():
    """Interface síncrona: loop em thread de background + run_coroutine_threadsafe."""
    bridge = OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )
    with bridge:
        assert bridge.runtime.orchestrator is not None
        bridge.runtime.register_provider(ScriptedProvider(["um", "dois", "três"]))

        r1 = bridge.process_text("primeiro turno")
        r2 = bridge.process_text("segundo turno")
        assert r1.content == "um" and r2.content == "dois"
        assert r1.conversation_id == r2.conversation_id == bridge.conversation_id

        bridge.new_conversation()
        r3 = bridge.process_text("terceiro turno, nova conversa")
        assert r3.content == "três"
        assert r3.conversation_id != r2.conversation_id

        status = bridge.status()
        assert status["ready"] is True
        assert status["default_provider"] == "mock"
        assert "mock" in status["providers"]

    # Após stop(), o estado real é reportado (nada simulado)
    assert bridge.status()["ready"] is False


def test_chat_sync_sem_start_levanta_erro_claro():
    bridge = OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    )
    try:
        bridge.process_text("msg")
        raise AssertionError("deveria ter levantado RuntimeError")
    except RuntimeError as exc:
        assert "start" in str(exc).lower()
    finally:
        bridge.stop()
