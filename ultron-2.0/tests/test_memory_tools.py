"""Testes da memória de fatos (Etapa 4).

Validação de que a memória:

* é EXPLÍCITA — nada grava sozinho em um turno de conversa comum;
* usa o gerenciador REAL do Mark-LVI, mas grava no arquivo PRÓPRIO do 2.0;
* nunca toca `Mark-LVI-main/memory/long_term.json`;
* `forget` é destrutivo e fica bloqueado pelo gate de confirmação enquanto a
  interface de confirmação não existir (recusar é o comportamento seguro).
"""

from __future__ import annotations

import json
from pathlib import Path

import ultron_2_0  # sys.path lain + Mark-LVI
from ultron_2_0.core_runtime import UltronCoreRuntime
from ultron_2_0.memory_tools import (
    MEMORY_CATEGORIES,
    FactMemory,
    configure_memory_path,
)
from ultron_2_0.tool_gateway import ToolGateway

from tests.fakes import ScriptedProvider

MARKLVI_LONG_TERM = (
    Path(ultron_2_0.bootstrap.resolve_roots()[2]) / "memory" / "long_term.json"
)


def test_remember_e_recall_usam_arquivo_do_2_0(tmp_path):
    path = tmp_path / "memory.json"
    memory = FactMemory(path)

    stored = memory.remember("cor_favorita", "vermelho", "preferences")
    assert stored["stored"] is True
    assert path.exists()

    found = memory.recall("cor favorita")
    assert "vermelho" in found
    assert "preferences" in found

    # Schema idêntico ao gerenciador reutilizado do Mark-LVI.
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["preferences"]["cor_favorita"]["value"] == "vermelho"
    assert "updated" in data["preferences"]["cor_favorita"]


def test_categoria_invalida_cai_em_notes(tmp_path):
    memory = FactMemory(tmp_path / "m.json")
    stored = memory.remember("k", "v", "categoria-inexistente")
    assert stored["category"] == "notes"
    assert stored["category"] in MEMORY_CATEGORIES


def test_chave_ou_valor_vazio_e_rejeitado(tmp_path):
    memory = FactMemory(tmp_path / "m.json")
    for key, value in (("", "v"), ("k", "  ")):
        try:
            memory.remember(key, value)
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError("esperava ValueError")


def test_forget_remove_fato_do_arquivo_do_2_0(tmp_path):
    memory = FactMemory(tmp_path / "m.json")
    memory.remember("projeto", "ULTRON 2.0", "projects")
    result = memory.forget("projeto", "projects")
    assert result["removed"] is True
    assert "ULTRON 2.0" not in memory.recall("projeto")


def test_gateway_bloqueia_forget_sem_interface_de_confirmacao(tmp_path):
    import asyncio

    gateway = ToolGateway()
    memory = FactMemory(tmp_path / "m.json")
    from ultron_2_0.memory_tools import register_memory_tools

    register_memory_tools(gateway, memory)
    memory.remember("segredo", "dado sensível")

    result = asyncio.run(gateway.execute("forget", {"key": "segredo"}))
    assert result.ok is False
    assert "confirmation" in (result.error or "")
    # Nada foi apagado.
    assert "dado sensível" in memory.recall("segredo")


def test_remember_e_recall_pelo_gateway(tmp_path):
    import asyncio

    gateway = ToolGateway()
    from ultron_2_0.memory_tools import register_memory_tools

    register_memory_tools(gateway, FactMemory(tmp_path / "m.json"))

    remember = asyncio.run(
        gateway.execute(
            "remember",
            {"key": "cidade", "value": "São Paulo", "category": "identity"},
        )
    )
    assert remember.ok is True
    payload = json.loads(remember.result)
    assert payload["stored"] is True

    recall = asyncio.run(gateway.execute("recall", {"query": "cidade"}))
    assert recall.ok is True
    assert "São Paulo" in json.loads(recall.result)["facts"]


def test_execucao_de_ferramenta_nao_grava_memoria_automaticamente():
    """Um turno comum (sem tool) não cria/altera o arquivo de memória."""
    import asyncio

    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=True,
    )
    try:
        asyncio.run(runtime.start_async())
        memory_path = runtime.memory.path
        before = (
            memory_path.stat().st_mtime_ns if memory_path.exists() else None
        )
        runtime.register_provider(ScriptedProvider(["conversa comum"]))
        asyncio.run(runtime.chat("oi, tudo bem?"))
        after = (
            memory_path.stat().st_mtime_ns if memory_path.exists() else None
        )
        assert after == before
    finally:
        asyncio.run(runtime.shutdown())


def test_long_term_json_do_marklvi_permanece_intocado():
    """O arquivo original nunca é criado/alterado pelo 2.0."""
    before = MARKLVI_LONG_TERM.stat().st_mtime_ns if MARKLVI_LONG_TERM.exists() else None
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=True,
    )
    try:
        import asyncio

        asyncio.run(runtime.start_async())
        assert runtime.memory is not None
        assert runtime.memory.path != MARKLVI_LONG_TERM
    finally:
        import asyncio

        asyncio.run(runtime.shutdown())

    after = MARKLVI_LONG_TERM.stat().st_mtime_ns if MARKLVI_LONG_TERM.exists() else None
    assert after == before
