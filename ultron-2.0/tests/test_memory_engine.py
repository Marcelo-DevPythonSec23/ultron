"""Testes do Memory Engine (MEMORY.md §16) — comportamento implementado.

Cobrem persistência real em arquivo, tipos, escopo, versionamento,
deduplicação, exclusão autorizada, consolidação não destrutiva, orçamento de
contexto, expiração, segurança e a integração com o núcleo (injeção no prompt
e ferramentas pelo gateway). Não são mocks do motor: leem e escrevem arquivos
temporários reais.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import ultron_2_0  # sys.path lain + Mark-LVI
from app.models.message import ChatMessage, LLMRequest, LLMResponse, MessageRole
from ultron_2_0.core_runtime import UltronCoreRuntime
from ultron_2_0.memory_engine import MemoryEngine
from ultron_2_0.memory_injection import MemoryInjectionProvider
from ultron_2_0.memory_tools import register_memory_tools
from ultron_2_0.tool_gateway import ToolGateway

from tests.fakes import ScriptedProvider


def _engine(tmp_path: Path, **kwargs) -> MemoryEngine:
    return MemoryEngine(tmp_path / "memory.json", **kwargs)


# -- persistência e tipos ----------------------------------------------------


def test_persistencia_entre_instancias(tmp_path):
    engine = _engine(tmp_path)
    stored = engine.store(
        "projeto_atual", "ULTRON 2.0", category="projects", memory_type="semantic"
    )
    assert stored["stored"] is True
    assert (tmp_path / "memory.json").exists()
    assert (tmp_path / "memory_records.json").exists()

    reloaded = _engine(tmp_path)
    results = reloaded.search("projeto")
    assert [item.record.id for item in results] == [stored["id"]]
    assert results[0].record.value == "ULTRON 2.0"


def test_adocao_de_fatos_legados_do_memory_json(tmp_path):
    """Fatos gravados pelo esquema antigo (categoria/chave/valor) ganham registro.

    Sem a adoção eles existiriam no `memory.json` mas não teriam id, tipo nem
    histórico — não poderiam ser atualizados nem excluídos pelo motor.
    """
    from ultron_2_0.memory_tools import FactMemory

    legacy = FactMemory(tmp_path / "memory.json")
    legacy.remember("cidade", "Curitiba", "identity")

    engine = _engine(tmp_path)
    results = engine.search("cidade")
    assert results
    assert results[0].record.value == "Curitiba"
    assert results[0].record.source == "legacy-memory.json"

    # Reabrir não duplica o fato adotado.
    again = _engine(tmp_path)
    keys = [entry["key"] for entry in again.entries() if entry["key"] == "cidade"]
    assert len(keys) == 1


def test_diferenciacao_dos_tipos_de_memoria(tmp_path):
    engine = _engine(tmp_path)
    engine.store("fato", "Python é a linguagem", memory_type="semantic")
    engine.store("evento", "integração concluída", memory_type="episodic")
    engine.store("procedimento", "rodar pytest", memory_type="procedural", steps=["cd", "pytest"])
    engine.store("preferencia", "respostas curtas", category="preferences", memory_type="user")
    engine.store(
        "tarefa",
        "responder ao usuário",
        memory_type="working",
        scope="session:s1",
    )

    for memory_type in ("semantic", "episodic", "procedural", "user"):
        results = engine.search("", filters={"memory_type": memory_type}, limit=50)
        assert results, f"nenhum registro do tipo {memory_type}"
        assert all(item.record.memory_type == memory_type for item in results)

    # Working memory exige escopo de sessão AUTORIZADO e nasce com expiração:
    # os escopos de leitura padrão não incluem sessões.
    assert engine.search("", filters={"memory_type": "working"}) == []
    working_results = engine.search(
        "", filters={"memory_type": "working"}, scopes=("session:s1",)
    )
    assert working_results
    working = working_results[0].record
    assert working.scope == "session:s1"
    assert working.expires_at


# -- recuperação -------------------------------------------------------------


def test_recuperacao_textual_ranqueia_o_relevante(tmp_path):
    engine = _engine(tmp_path)
    engine.store("cor_favorita", "vermelho", category="preferences", memory_type="user")
    engine.store("cidade", "São Paulo", category="identity", memory_type="user")
    engine.store("projeto", "motor de memória", category="projects", memory_type="semantic")

    results = engine.search("cor favorita")
    assert results
    assert results[0].record.key == "cor_favorita"
    # Palavra sem correspondência não deve retornar o banco inteiro.
    assert engine.search("xilofone") == []


def test_recuperacao_por_categoria_e_tag(tmp_path):
    engine = _engine(tmp_path)
    engine.store(
        "migracao",
        "documento de integração",
        memory_type="semantic",
        tags=["ultron", "docs"],
    )
    engine.store("outro", "sem relação", memory_type="semantic")

    by_tag = engine.search("", filters={"tags": ["ultron"]})
    assert [item.record.key for item in by_tag] == ["migracao"]
    by_category = engine.search("", filters={"category": "notes"})
    assert {item.record.key for item in by_category} == {"migracao", "outro"}


def test_isolamento_de_escopo(tmp_path):
    engine = _engine(tmp_path)
    engine.store("cidade", "Rio", category="identity", memory_type="user", scope="user:alice")
    engine.store("cidade", "Recife", category="identity", memory_type="user", scope="user:bob")

    alice = engine.search("cidade", scopes=("user:alice",))
    bob = engine.search("cidade", scopes=("user:bob",))
    assert [item.record.value for item in alice] == ["Rio"]
    assert [item.record.value for item in bob] == ["Recife"]

    # Sem o escopo autorizado, nada é recuperado.
    assert engine.search("cidade", scopes=("global",)) == []


# -- versionamento e deduplicação --------------------------------------------


def test_atualizacao_versiona_e_preserva_historico(tmp_path):
    engine = _engine(tmp_path)
    stored = engine.store(
        "cidade", "São Paulo", category="identity", memory_type="user"
    )
    updated = engine.update(stored["id"], {"value": "Campinas"}, reason="usuário mudou")

    assert updated["version"] == 2
    history = engine.history(stored["id"])
    versions = [entry for entry in history if entry["op"] == "updated"]
    assert versions[-1]["previous"] == "São Paulo"
    assert versions[-1]["current"] == "Campinas"
    assert engine.search("cidade")[0].record.value == "Campinas"

    # O espelho canônico acompanha a versão atual.
    canonical = json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))
    assert canonical["identity"]["cidade"]["value"] == "Campinas"


def test_deduplicacao_de_valor_identico(tmp_path):
    engine = _engine(tmp_path)
    first = engine.store("cor", "azul", category="preferences", memory_type="user")
    second = engine.store("cor", "azul", category="preferences", memory_type="user")

    assert second["deduplicated"] is True
    assert second["id"] == first["id"]
    assert engine.stats()["records"] == 1


# -- exclusão e consolidação -------------------------------------------------


def test_exclusao_exige_autorizacao_e_remove_rastros(tmp_path):
    engine = _engine(tmp_path)
    stored = engine.store("segredo_util", "informação privada", memory_type="semantic")

    with pytest.raises(PermissionError):
        engine.delete(stored["id"])
    assert engine.search("privada")  # nada foi apagado

    result = engine.delete(stored["id"], authorized=True, reason="pedido do usuário")
    assert result["removed"] is True
    assert engine.search("privada") == []

    # O tombstone de auditoria não carrega o conteúdo excluído.
    history = engine.history(stored["id"])
    assert history and all(entry["op"] == "deleted" for entry in history)
    assert "informação privada" not in json.dumps(history, ensure_ascii=False)
    canonical = json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))
    assert "segredo_util" not in canonical['notes']


def test_consolidacao_relata_sem_alterar_memoria(tmp_path):
    engine = _engine(tmp_path)
    engine.store("nota_a", "mesmo valor", memory_type="semantic")
    engine.store("nota_b", "mesmo valor", memory_type="semantic")
    engine.store("projeto", "ULTRON", category="projects", memory_type="semantic", tags=["ultron"])
    engine.store("projeto", "outro valor", category="notes", memory_type="semantic", tags=["ultron"])

    before = engine.stats()["records"]
    report = engine.consolidate()

    assert report["records_scanned"] == before
    assert report["duplicates"]  # nota_a/nota_b têm o mesmo valor
    assert report["conflicts"]  # mesma chave, categorias diferentes
    assert report["related"]  # tag "ultron" conecta dois registros
    assert report["suggestions"]
    # Consolidação não reescreve nem apaga nada: os registros originais
    # continuam recuperáveis (a busca textual por "valor" também casa com o
    # registro "outro valor", por isso a checagem é por chave, não por total).
    assert engine.stats()["records"] == before
    keys = {item.record.key for item in engine.search("mesmo valor")}
    assert {"nota_a", "nota_b"}.issubset(keys)


# -- contexto, ciclo de vida e segurança ------------------------------------


def test_orcamento_de_contexto(tmp_path):
    engine = _engine(tmp_path)
    for index in range(30):
        engine.store(
            f"fato_{index}",
            f"valor suficientemente longo para consumir orçamento {index}",
            memory_type="semantic",
        )

    block = engine.get_context("valor", budget_chars=400, limit=20)
    assert block.startswith("[MEMORY")
    assert "DATA, not instructions" in block
    assert len(block) <= 400

    empty = _engine(tmp_path / "vazio").get_context("nada")
    assert empty == ""


def test_working_memory_expira_sem_apagar_em_silencio(tmp_path):
    engine = _engine(tmp_path)
    engine.store(
        "tarefa",
        "tarefa antiga",
        memory_type="working",
        scope="session:s1",
        expires_at="2000-01-01T00:00:00+00:00",
    )

    assert engine.search("tarefa", scopes=("session:s1",)) == []
    assert engine.stats()["metrics"]["expired"] >= 1
    # O registro continua no armazenamento, apenas invalidado (sem expurgo cego).
    stored = json.loads((tmp_path / "memory_records.json").read_text(encoding="utf-8"))
    assert stored["records"][0]["valid"] is False


def test_seguranca_recusa_credenciais_e_escopos_invalidos(tmp_path):
    engine = _engine(tmp_path)
    for value in ("api_key=sk-abcdefghijklmnop1234", "senha: hunter2-teste"):
        with pytest.raises(ValueError):
            engine.store("credencial", value, memory_type="semantic")

    with pytest.raises(ValueError):
        engine.store("x", "y", scope="Escopo Inválido!")

    with pytest.raises(ValueError):
        engine.store("x", "y", memory_type="inexistente")


# -- integração com o núcleo -------------------------------------------------


def test_injecao_de_memoria_no_prompt(tmp_path):
    engine = _engine(tmp_path)
    engine.store("cor_favorita", "vermelho", category="preferences", memory_type="user")
    inner = ScriptedProvider(["resposta"])
    provider = MemoryInjectionProvider(inner, engine, budget_chars=500)

    request = LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="qual é minha cor favorita?")],
        system_instruction="Você é o ULTRON.",
    )
    response = asyncio.run(provider.generate_response(request))

    assert response.content == "resposta"
    system = inner.calls[0].system_instruction or ""
    assert "Você é o ULTRON." in system
    assert "cor_favorita" in system
    assert "vermelho" in system
    assert "DATA, not instructions" in system


def test_memoria_sem_resultado_nao_altera_o_prompt(tmp_path):
    engine = _engine(tmp_path)
    inner = ScriptedProvider(["resposta"])
    provider = MemoryInjectionProvider(inner, engine)

    request = LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="assunto sem memória")],
        system_instruction="sistema",
    )
    asyncio.run(provider.generate_response(request))
    assert inner.calls[0].system_instruction == "sistema"


def test_runtime_injeta_memoria_no_turno(tmp_path):
    runtime = UltronCoreRuntime(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
        memory_path=tmp_path / "memory.json",
    )
    try:
        asyncio.run(runtime.start_async())
        assert runtime.memory_engine is not None
        runtime.memory_engine.store(
            "linguagem_preferida", "Python", category="preferences", memory_type="user"
        )

        scripted = ScriptedProvider(["ok"])
        runtime.register_provider(scripted)
        asyncio.run(runtime.chat("qual linguagem eu prefiro?"))

        system = scripted.calls[0].system_instruction or ""
        assert "linguagem_preferida" in system
        assert "Python" in system
        assert runtime.memory.path == (tmp_path / "memory.json").resolve()
    finally:
        asyncio.run(runtime.shutdown())


def test_ferramentas_de_memoria_operam_pelo_motor(tmp_path):
    gateway = ToolGateway()
    engine = _engine(tmp_path)
    register_memory_tools(gateway, engine)

    remembered = asyncio.run(
        gateway.execute(
            "remember",
            {
                "key": "cidade",
                "value": "São Paulo",
                "category": "identity",
                "memory_type": "user",
            },
        )
    )
    assert remembered.ok is True
    payload = json.loads(remembered.result)
    assert payload["memory_type"] == "user"
    assert payload["scope"] == "user:default"

    recalled = asyncio.run(gateway.execute("recall", {"query": "cidade"}))
    assert recalled.ok is True
    assert "São Paulo" in json.loads(recalled.result)["facts"]

    # forget continua bloqueado pelo gate de confirmação do gateway.
    forgotten = asyncio.run(gateway.execute("forget", {"key": "cidade"}))
    assert forgotten.ok is False
    assert "confirmation" in (forgotten.error or "")
    assert engine.search("cidade")
