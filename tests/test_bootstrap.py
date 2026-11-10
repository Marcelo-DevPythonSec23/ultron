"""Testes do bootstrap: caminhos absolutos e banco isolado (Teste A)."""

from __future__ import annotations

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
