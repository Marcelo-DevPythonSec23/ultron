"""Teste E ponta a ponta: ferramenta REAL do Mark-LVI via orquestrador do lain.

Caminho completo validado (master prompt §7.2):

    mensagem do usuário
        -> Orchestrator do lain (persistência + contexto + prompt)
            -> ToolCallingProvider (protocolo JSON no system prompt)
                -> decisão JSON do modelo (ScriptedProvider, sem rede)
                    -> ToolGateway (validação, worker thread, timeout)
                        -> actions/system_monitor.py do Mark-LVI (psutil)
                            -> resultado como DADO marcado
                                -> modelo novamente -> resposta final
                                    -> persistida pelo ChatService do lain

A ferramenta usada é `system_status` (leitura não destrutiva de métricas).
"""

from __future__ import annotations

import json

import ultron_2_0  # sys.path lain + Mark-LVI
from ultron_2_0.core_runtime import UltronCoreRuntime

from tests.fakes import ScriptedProvider


async def test_ferramenta_real_do_marklvi_ponta_a_ponta():
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=True,
    )
    try:
        await runtime.start_async()
        assert runtime.gateway is not None
        assert "system_status" in runtime.gateway.names()

        # 1ª resposta: decisão de ferramenta (JSON do protocolo).
        # 2ª resposta: texto final para o usuário.
        scripted = ScriptedProvider(
            [
                json.dumps({"tool": "system_status", "args": {}}),
                "CPU em X%, tudo normal.",
            ]
        )
        runtime.register_provider(scripted)  # substitui o mock, com o MESMO id

        response = await runtime.chat("como está o sistema agora?")

        # Resposta final do modelo após interpretar o resultado da ferramenta
        assert response.content == "CPU em X%, tudo normal."

        # Duas chamadas ao modelo: decisão + resposta final
        assert len(scripted.calls) == 2

        # O system prompt da 1ª chamada carrega o protocolo + declarações
        first_prompt = scripted.calls[0].system_instruction or ""
        assert "TOOL PROTOCOL" in first_prompt
        assert "system_status" in first_prompt

        # A 2ª chamada recebeu o resultado REAL da execução (psutil) como DADO
        second_contents = [m.content for m in scripted.calls[1].messages]
        tool_result = next(c for c in second_contents if c.startswith("[TOOL_RESULT"))
        assert "cpu_percent" in tool_result  # métrica real de psutil
        assert "status=done action=system_status" in tool_result

        # Rastro de execução PERSISTIDO: o orquestrador grava raw_metadata do
        # LLMResponse como JSON em MessageModel.raw_metadata (lain
        # record_assistant_message). ChatResponse NÃO carrega raw_metadata —
        # campo verificado antes de usar. Buscamos a mensagem persistida.
        messages = await runtime.orchestrator.chat_service.msg_repo.get_messages_by_conversation(
            conversation_id=response.conversation_id
        )
        assistant_rows = [m for m in messages if m.role == "assistant"]
        assert assistant_rows, "mensagem do assistente não foi persistida"
        persisted_meta = json.loads(assistant_rows[-1].raw_metadata or "{}")
        assert persisted_meta.get("tool_calls")[0]["tool"] == "system_status"
        assert persisted_meta["tool_calls"][0]["ok"] is True
        assert response.message_id == assistant_rows[-1].id

        # Persistência do turno completo no banco em memória
        history = await runtime.orchestrator.chat_service.get_recent_chat_messages(
            conversation_id=response.conversation_id
        )
        contents = [m.content for m in history]
        assert "como está o sistema agora?" in contents
        assert "CPU em X%, tudo normal." in contents
    finally:
        await runtime.shutdown()


async def test_turno_sem_ferramenta_nao_inocula_protocolo_na_resposta():
    """Conversa comum: ferramentas disponíveis mas o modelo responde texto."""
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=True,
    )
    try:
        await runtime.start_async()
        scripted = ScriptedProvider(["só conversando, sem ferramenta"])
        runtime.register_provider(scripted)

        response = await runtime.chat("oi, tudo bem?")
        assert response.content == "só conversando, sem ferramenta"
        # Uma única chamada: nenhuma ferramenta foi disparada
        assert len(scripted.calls) == 1
        # Sem rastro de ferramenta na mensagem persistida
        messages = await runtime.orchestrator.chat_service.msg_repo.get_messages_by_conversation(
            conversation_id=response.conversation_id
        )
        assistant_rows = [m for m in messages if m.role == "assistant"]
        persisted_meta = json.loads(assistant_rows[-1].raw_metadata or "{}")
        assert "tool_calls" not in persisted_meta
    finally:
        await runtime.shutdown()


# -- Fase 2: autorização interativa ponta a ponta ----------------------------


def _runtime_com_autorizacao(tmp_path, approved):
    from ultron_2_0.authorization import AuthorizationManager

    seen: list = []

    def confirm(action):
        seen.append(action)
        return approved

    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=True,
        memory_path=tmp_path / "memory.json",
        authorization=AuthorizationManager(confirm_handler=confirm),
    )
    return runtime, seen


async def test_forget_real_so_executa_apos_aprovacao(tmp_path):
    runtime, seen = _runtime_com_autorizacao(tmp_path, approved=True)
    try:
        await runtime.start_async()
        runtime.memory_engine.remember(
            "cor_favorita", "vermelho", category="preferences"
        )
        assert "vermelho" in runtime.memory_engine.recall("")

        scripted = ScriptedProvider(
            [
                json.dumps(
                    {
                        "tool": "forget",
                        "args": {"key": "cor_favorita", "category": "preferences"},
                    }
                ),
                "Fato esquecido.",
            ]
        )
        runtime.register_provider(scripted)

        response = await runtime.chat("esqueça minha cor favorita")

        assert response.content == "Fato esquecido."
        assert len(seen) == 1
        assert seen[0].tool_name == "forget"
        assert "vermelho" not in runtime.memory_engine.recall("")

        messages = await runtime.orchestrator.chat_service.msg_repo.get_messages_by_conversation(
            conversation_id=response.conversation_id
        )
        assistant = [m for m in messages if m.role == "assistant"][-1]
        calls = json.loads(assistant.raw_metadata or "{}")["tool_calls"]
        assert calls[0]["tool"] == "forget"
        assert calls[0]["ok"] is True
    finally:
        await runtime.shutdown()


async def test_forget_real_nao_executa_quando_recusado(tmp_path):
    runtime, seen = _runtime_com_autorizacao(tmp_path, approved=False)
    try:
        await runtime.start_async()
        runtime.memory_engine.remember(
            "cor_favorita", "vermelho", category="preferences"
        )

        scripted = ScriptedProvider(
            [
                json.dumps(
                    {
                        "tool": "forget",
                        "args": {"key": "cor_favorita", "category": "preferences"},
                    }
                ),
                "Não vou apagar sem confirmação.",
            ]
        )
        runtime.register_provider(scripted)

        response = await runtime.chat("esqueça minha cor favorita")

        assert response.content == "Não vou apagar sem confirmação."
        assert len(seen) == 1
        # O fato continua na memória: recusa significa NÃO executar.
        assert "vermelho" in runtime.memory_engine.recall("")

        messages = await runtime.orchestrator.chat_service.msg_repo.get_messages_by_conversation(
            conversation_id=response.conversation_id
        )
        assistant = [m for m in messages if m.role == "assistant"][-1]
        calls = json.loads(assistant.raw_metadata or "{}")["tool_calls"]
        assert calls[0]["ok"] is False
    finally:
        await runtime.shutdown()
