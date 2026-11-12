"""Testes do bootstrap: caminhos absolutos e banco isolado (Teste A)."""

from __future__ import annotations

import os

from ultron_2_0 import bootstrap


def test_roots_resolvidas():
    root, lain, marklvi = bootstrap.resolve_roots()
    assert lain.is_dir() and lain.name == "lain"
    assert marklvi.is_dir() and marklvi.name == "Mark-LVI-main"
    assert root == lain.parent == marklvi.parent


def test_ensure_sys_paths_idempotente():
    first = bootstrap.ensure_sys_paths()
    second = bootstrap.ensure_sys_paths()
    assert first == second


def test_banco_padrao_isolado_do_lain():
    url = bootstrap.default_database_url()
    # Banco do 2.0, em ultron-2.0/data/ — JAMAIS lain/ultron.db.
    assert url.endswith("/ultron-2.0/data/ultron2.db")
    assert "lain/ultron.db" not in url


def test_settings_sobrescreve_database_url():
    settings = bootstrap.build_settings(
        bootstrap.resolve_project_root() / "lain",
        database_url="sqlite+aiosqlite:///:memory:",
    )
    assert settings.DATABASE_URL == "sqlite+aiosqlite:///:memory:"


def test_settings_padrao_aponta_para_banco_do_2_0():
    settings = bootstrap.build_settings(bootstrap.resolve_project_root() / "lain")
    assert settings.DATABASE_URL.endswith("data/ultron2.db")
    assert "lain/ultron.db" not in settings.DATABASE_URL


def test_settings_carrega_env_do_lain_por_caminho_absoluto():
    """O .env do lain é lido de qualquer CWD; a chave (se existir) não é
    impressa nem copiada — só verificamos que Settings carrega."""
    settings = bootstrap.build_settings(bootstrap.resolve_project_root() / "lain")
    assert settings.APP_NAME == "ULTRON"


def test_load_env_carrega_variaveis_do_arquivo(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ULTRON_TEST_LOAD_ENV=carregado\n", encoding="utf-8")
    monkeypatch.delenv("ULTRON_TEST_LOAD_ENV", raising=False)

    loaded = bootstrap.load_env(env_file)

    assert loaded == env_file.resolve()
    assert os.environ["ULTRON_TEST_LOAD_ENV"] == "carregado"


def test_load_env_nao_sobrescreve_ambiente_existente(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ULTRON_TEST_LOAD_ENV=arquivo\n", encoding="utf-8")
    monkeypatch.setenv("ULTRON_TEST_LOAD_ENV", "shell")

    bootstrap.load_env(env_file)

    # Precedência: variáveis exportadas no shell vencem o .env.
    assert os.environ["ULTRON_TEST_LOAD_ENV"] == "shell"


def test_load_env_arquivo_ausente_nao_falha(tmp_path):
    assert bootstrap.load_env(tmp_path / "nao_existe.env") is None


def test_load_env_padrao_usa_ultron2_root():
    """O caminho padrão é o .env da raiz do produto, não o do CWD."""
    assert bootstrap.load_env(bootstrap.ULTRON2_ROOT / "nao_existe.env") is None
    assert bootstrap.ULTRON2_ROOT.name == "ultron-2.0"
