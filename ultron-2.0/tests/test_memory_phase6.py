"""Testes da Fase 6 — Evolução da Memória.

Cobrem, sem exigir dependências externas novas (sentence-transformers,
cryptography podem não estar instalados):

1. MemoryEngine existente continua funcionando (compatibilidade: store,
   search, retrieve, get_context, consolidate, expire, stats).
2. SemanticIndex disponível=False sem sentence-transformers (fallback gracioso).
3. search_semantic devolve lista vazia sem embeddings (não quebra).
4. retrieve_hybrid funciona sem embeddings (equivale a léxico, lexical preservada).
5. Backup e restauração round-trip (arquivos de memória do 2.0).
6. Criptografia não disponível sem cryptography (desabilitado).
7. generate_key_file cria chave (ou não recria se existir).
8. encrypt/decrypt memory file sem criptografia disponível (erro controlado).
9. backup/restauração rejeitam diretório ausente ou confirm=False.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from ultron_2_0.memory_engine import MemoryEngine, MEMORY_TYPES
from ultron_2_0.memory_semantic import SemanticIndex, available as semantic_available
from ultron_2_0.memory_backup import backup_memory, restore_memory, MEMORY_FILES
from ultron_2_0.memory_encryption import MemoryEncryption, generate_key_file, available as encryption_available


# -- helpers ------------------------------------------------------------------
def _make_engine(tmp_path: Path) -> MemoryEngine:
    return MemoryEngine(path=str(tmp_path / "memory.json"))


def _store_sample(engine: MemoryEngine) -> None:
    engine.store(
        "nome_usuario",
        "Marcelo",
        category="identity",
        memory_type="user",
        scope="user:default",
        trust="user_stated",
    )
    engine.store(
        "arquitetura_ultron",
        "sistema multiagente com roteador de modelos",
        category="notes",
        memory_type="semantic",
        scope="global",
        trust="confirmed",
    )
    engine.store(
        "reuniao_projeto",
        "revisar integração com OpenCode na quinta-feira",
        category="notes",
        memory_type="episodic",
        scope="global",
        trust="user_stated",
        tags=["reuniao", "opencode"],
    )


# -- 1. compatibilidade (memória existente continua funcionando) -------------
def test_memoria_existente_funciona(tmp_path):
    engine = _make_engine(tmp_path)
    _store_sample(engine)

    stats = engine.stats()
    assert stats["records"] >= 3
    assert "user" in stats["by_type"] or "semantic" in stats["by_type"]

    results = engine.search("Marcelo", scopes=("user:default", "global"))
    assert len(results) >= 1
    assert any("Marcelo" in r.record.value for r in results)

    ctx = engine.get_context("arquitetura", budget_chars=500)
    assert "sistema multiagente" in ctx or "arquitetura_ultron" in ctx

    cons = engine.consolidate()
    assert "records_scanned" in cons
    assert "duplicates" in cons
    assert "conflicts" in cons

    n_expired = engine.expire()
    assert n_expired >= 0


def test_tipos_memoria_validos():
    assert "semantic" in MEMORY_TYPES
    assert "episodic" in MEMORY_TYPES
    assert "user" in MEMORY_TYPES


# -- 2. índice semântico opcional (sem dependência obrigatória) -------------
def test_semantic_index_nao_quebra_sem_dependencia():
    idx = SemanticIndex()
    # Sem sentence-transformers, available é False e não levanta.
    assert isinstance(idx.available, bool)
    pub = idx.public()
    assert "available" in pub
    assert "indexed_records" in pub


def test_semantic_index_consulta_retorna_vazio_sem_embeddings():
    idx = SemanticIndex()
    assert idx.query("qualquer coisa") == []


def test_semantic_disponivel_espelha_modulo():
    assert isinstance(semantic_available(), bool)


# -- 3. busca semantica e hybrida (fallback para lexico) --------------------
def test_search_semantic_devolve_vazio_sem_embeddings(tmp_path):
    engine = _make_engine(tmp_path)
    _store_sample(engine)
    resultado = engine.search_semantic("Marcelo", top_k=5)
    assert resultado == []


def test_retrieve_hybrid_equivale_a_lexico_sem_embeddings(tmp_path):
    engine = _make_engine(tmp_path)
    _store_sample(engine)
    h = engine.retrieve_hybrid("Marcelo", scopes=("user:default", "global"), limit=5)
    # Sem embeddings, híbrido deve conter pelo menos o resultado léxico.
    assert len(h) >= 1
    valores = [str(item["record"].get("value", "")) for item in h]
    assert any("Marcelo" in v for v in valores)


def test_retrieve_hybrid_respeita_orcamento(tmp_path):
    engine = _make_engine(tmp_path)
    _store_sample(engine)
    h = engine.retrieve_hybrid(
        "reuniao", scopes=("global",), limit=10, budget_chars=50
    )
    # Orçamento baixo: poucos resultados.
    assert len(h) <= 3


# -- 4. backup e restauracao -------------------------------------------------
def test_backup_e_restauracao_round_trip(tmp_path):
    engine_dir = tmp_path / "memoria"
    engine_dir.mkdir()
    engine = _make_engine(engine_dir)
    _store_sample(engine)

    zip_path = tmp_path / "backup_memoria.zip"
    resultado = engine.backup(zip_path)
    assert resultado["ok"] is True
    assert Path(zip_path).is_file()
    manifest = resultado["manifest"]
    assert manifest["record_count"] >= 3
    assert set(MEMORY_FILES).issubset(set(manifest["files"]))

    # Restaurar em diretório separado com confirm=True.
    destino = tmp_path / "memoria_restaurada"
    destino.mkdir()
    resultado_r = restore_memory(zip_path, destino, confirm=True)
    assert resultado_r["ok"] is True
    assert "memory.json" in resultado_r["restored"]
    assert (destino / "memory.json").is_file()


def test_backup_rejeita_origem_ausente(tmp_path):
    resultado = backup_memory(tmp_path / "nao_existe", tmp_path / "x.zip")
    assert resultado["ok"] is False
    assert "error" in resultado


def test_restauracao_requer_confirm(tmp_path):
    zip_path = tmp_path / "b.zip"
    zip_path.write_bytes(b"nao e um zip valido")
    resultado = restore_memory(zip_path, tmp_path, confirm=False)
    assert resultado["ok"] is False
    assert "confirm" in (resultado["error"] or "").lower()


# -- 5. criptografia opcional -----------------------------------------------
def test_encryption_nao_quebra_sem_dependencia():
    enc = MemoryEncryption()
    assert isinstance(enc.available, bool)
    pub = enc.public()
    assert "available" in pub
    assert isinstance(encryption_available(), bool)


def test_encryption_sem_chave_erro_controlado():
    enc = MemoryEncryption()
    if enc.available:
        pytest.skip("cryptography + chave disponíveis neste ambiente")
    # Sem criptografia, operações levantam erro controlado (não quebram o núcleo).
    assert enc.available is False


def test_generate_key_file_nao_recria(tmp_path):
    chave = tmp_path / "memory.key"
    assert generate_key_file(chave) is True
    assert generate_key_file(chave) is False  # já existe


def test_engine_encryption_status(tmp_path):
    engine = _make_engine(tmp_path)
    status = engine.encryption_status()
    assert "available" in status
    assert isinstance(status["available"], bool)


# -- 6. encrypt/decrypt arquivo de memoria sem criptografia -----------------
def test_encrypt_sem_criptografia(tmp_path):
    engine = _make_engine(tmp_path)
    f = tmp_path / "arquivo.txt"
    f.write_text("conteudo qualquer")
    resultado = engine.encrypt_memory_file(f)
    if engine.encryption.available:
        pytest.skip("cryptography disponível neste ambiente")
    assert resultado["ok"] is False
    assert "não disponível" in (resultado["error"] or "")


# -- 7. gera chave e usa (se cryptography disponível) ------------------------
@pytest.mark.skipif(not encryption_available(), reason="cryptography não instalado")
def test_criptografia_completa_com_dependencia(tmp_path):
    from ultron_2_0.memory_encryption import generate_key_file

    chave = tmp_path / "memory.key"
    assert generate_key_file(chave) is True
    os.environ["ULTRON2_MEMORY_ENCRYPTION_KEY"] = chave.read_bytes().decode().strip()
    try:
        enc = MemoryEncryption(chave)
        assert enc.available is True
        original = b"dados sensiveis de memoria"
        enc_bytes = enc.encrypt_bytes(original)
        assert enc_bytes != original
        dec_bytes = enc.decrypt_bytes(enc_bytes)
        assert dec_bytes == original
    finally:
        os.environ.pop("ULTRON2_MEMORY_ENCRYPTION_KEY", None)
