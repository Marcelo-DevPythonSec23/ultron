"""Testes do loop de tool calling: protocolo JSON entre modelo e gateway.

Fluxo validado (master prompt §7.2): mensagem do usuário -> orquestrador do
lain -> ToolCallingProvider (proxy) -> decisão JSON do modelo -> validação ->
execução autorizada -> resultado como DADO marcado -> modelo novamente ->
resposta final ao usuário. Provedor scriptável — sem rede, sem cotas.
"""

from __future__ import annotations

import json

import ultron_2_0  # sys.path lain + Mark-LVI
from app.models.message import ChatMessage, LLMRequest, MessageRole
from ultron_2_0.tool_gateway import ToolGateway
from ultron_2_0.tool_contracts import ToolContract
from ultron_2_0.tool_loop import TOOL_RESULT_TAG, ToolCallingProvider

from tests.fakes import ScriptedProvider


def _mini_gateway() -> ToolGateway:
    """Gateway mínimo com uma ferramenta fake determinística e não destrutiva."""
    gateway = ToolGateway()

    def echo_tool(parameters: dict) -> str:
        return json.dumps({"echo": parameters.get("query", "?"), "len": len(parameters.get("query", ""))})

    gateway.register(
        ToolContract(
            name="echo_tool",
            description="Echoes the query parameter back with its length.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Text to echo"},
                },
                "required": ["query"],
            },
            required_fields=["query"],
            timeout_seconds=5.0,
        ),
        echo_tool,
    )
    return gateway


def _request(message: str = "use a ferramenta") -> LLMRequest:
    return LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content=message)],
        system_instruction="You are ULTRON.",
    )


async def test_resposta_sem_tool_passa_direto():
    """Sem JSON de ferramenta na resposta, o proxy é transparente."""
    gateway = _mini_gateway()
    provider = ScriptedProvider(["resposta comum, sem JSON"])
    proxy = ToolCallingProvider(provider, gateway)

    response = await proxy.generate_response(_request())
    assert response.content == "resposta comum, sem JSON"
    assert len(provider.calls) == 1
    # O system prompt do modelo RECEBEU as declarações de ferramentas
    assert "echo_tool" in (provider.calls[0].system_instruction or "")
    assert "tool_calls" not in (response.raw_metadata or {})


async def test_ciclo_completo_tool_call_e_resposta_final():
    """Decisão JSON -> execução real -> resultado como DADO -> resposta final."""
    gateway = _mini_gateway()
    call_json = json.dumps({"tool": "echo_tool", "args": {"query": "olar"}})
    provider = ScriptedProvider([call_json, "resposta final após a ferramenta"])
    proxy = ToolCallingProvider(provider, gateway)

    response = await proxy.generate_response(_request())
    assert response.content == "resposta final após a ferramenta"

    # Duas chamadas ao modelo: a decisão e a resposta final
    assert len(provider.calls) == 1 + 1

    # A 2ª chamada carrega a 1ª resposta + o resultado marcado como DADO
    second = provider.calls[1]
    contents = [m.content for m in second.messages]
    assert call_json in contents  # histórico da decisão do modelo
    assert any(c.startswith(TOOL_RESULT_TAG) for c in contents)
    tool_result_msg = next(c for c in contents if c.startswith(TOOL_RESULT_TAG))
    assert "echo_tool" in tool_result_msg
    assert '"olar"' in tool_result_msg  # resultado real da execução
    # Papéis corretos: decisão como assistant, resultado como user (dado)
    roles = [(m.role, c[: len(TOOL_RESULT_TAG)]) for m, c in zip(second.messages, contents)]
    assert (MessageRole.ASSISTANT, call_json[: len(TOOL_RESULT_TAG)]) in roles

    # Rastro de ferramentas anexado à resposta final
    trace = (response.raw_metadata or {}).get("tool_calls")
    assert trace and trace[0]["tool"] == "echo_tool" and trace[0]["ok"] is True

    # Prompt de sistema com protocolo na 2ª rodada também
    assert "echo_tool" in (second.system_instruction or "")


async def test_tool_desconhecida_vira_erro_reportavel_ao_modelo():
    """O modelo chama ferramenta inexistente: o gateway recusa e o resultado
    de falha volta como DADO — o modelo decide o que dizer (Teste G)."""
    gateway = _mini_gateway()
    bad_call = json.dumps({"tool": "nao_existe", "args": {}})
    provider = ScriptedProvider([bad_call, "desculpe, não tenho essa ferramenta"])
    proxy = ToolCallingProvider(provider, gateway)

    response = await proxy.generate_response(_request())
    assert response.content == "desculpe, não tenho essa ferramenta"

    tool_result_msg = next(
        c for c in (m.content for m in provider.calls[1].messages) if c.startswith(TOOL_RESULT_TAG)
    )
    assert "failed" in tool_result_msg
    assert "unknown tool" in tool_result_msg


async def test_parametro_obrigatorio_ausente_recusado():
    gateway = _mini_gateway()
    provider = ScriptedProvider(
        [json.dumps({"tool": "echo_tool", "args": {}}), "falto com o parâmetro"]
    )
    proxy = ToolCallingProvider(provider, gateway)
    response = await proxy.generate_response(_request())
    assert response.content == "falto com o parâmetro"
    tool_result_msg = next(
        c for c in (m.content for m in provider.calls[1].messages) if c.startswith(TOOL_RESULT_TAG)
    )
    assert "missing required parameter 'query'" in tool_result_msg


async def test_teto_de_rodadas_e_respeitado():
    """Modelo que chama ferramentas sem parar: teto de rodadas força resposta.

    Contagem com max_rounds=2: chamada 1 (tool call) -> executa; chamada 2
    (tool call) -> executa; chamada 3 (tool call) -> descartada, break;
    chamada 4 (final, sem ferramentas) -> resposta devolvida. Total = 4.
    """
    gateway = _mini_gateway()
    endless = json.dumps({"tool": "echo_tool", "args": {"query": "de novo"}})
    provider = ScriptedProvider(
        [endless, endless, endless, "fim por teto de rodadas"]
    )
    proxy = ToolCallingProvider(provider, gateway, max_rounds=2)

    response = await proxy.generate_response(_request())
    assert len(provider.calls) == 4
    assert response.content == "fim por teto de rodadas"
    assert (response.raw_metadata or {}).get("tool_loop_capped") is True
    assert len((response.raw_metadata or {}).get("tool_calls", [])) == 2
    # A chamada final recebeu a instrução de não chamar mais ferramentas
    final_msg = provider.calls[3].messages[-1].content
    assert "Tool call limit reached" in final_msg


async def test_json_cercado_de_prosa_e_detectado():
    """O modelo cerca o JSON de texto/fences: a varredura tolerante acha."""
    gateway = _mini_gateway()
    provider = ScriptedProvider(
        [
            f'Claro!\n```json\n{{"tool": "echo_tool", "args": {{"query": "x"}}}}\n```\n',
            "pronto",
        ]
    )
    proxy = ToolCallingProvider(provider, gateway)
    response = await proxy.generate_response(_request())
    assert response.content == "pronto"
    assert (response.raw_metadata or {}).get("tool_calls")


async def test_gateway_vazio_deixa_proxy_transparente():
    """Sem ferramentas registradas, o proxy não injeta protocolo algum."""
    gateway = ToolGateway()
    provider = ScriptedProvider(["resposta direta"])
    proxy = ToolCallingProvider(provider, gateway)
    response = await proxy.generate_response(_request())
    assert response.content == "resposta direta"
    assert "TOOL PROTOCOL" not in (provider.calls[0].system_instruction or "")


async def test_streaming_entrega_resposta_final_unica():
    """Streaming com protocolo: chunk único com a resposta final (documentado).

    O contrato do lain para on_chunk é Callable[[str], None] SÍNCRONO (o
    MockProvider dele usa callback sync) — o teste usa um callback comum.
    """
    gateway = _mini_gateway()
    provider = ScriptedProvider(["resposta única"])
    proxy = ToolCallingProvider(provider, gateway)

    chunks: list[str] = []
    response = await proxy.generate_response_streaming(_request(), chunks.append)
    assert response.content == "resposta única"
    assert chunks == ["resposta única"]


async def test_health_e_identidade_delegados():
    gateway = _mini_gateway()
    provider = ScriptedProvider(["x"])
    proxy = ToolCallingProvider(provider, gateway)
    assert proxy.provider_id == "mock"
    assert proxy.default_model == "scripted-model"
    assert await proxy.health_check() is True
