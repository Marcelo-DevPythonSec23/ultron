"""Testes unitários para o módulo de configurações."""

import os
from unittest.mock import patch

from app.config import Settings, get_settings


def test_settings_defaults():
    """Valida que as configurações padrão são atribuídas corretamente."""
    settings = Settings()
    assert settings.APP_NAME == "ULTRON"
    assert settings.DEFAULT_LLM_PROVIDER in ["gemini", "mock"]
    assert settings.MAX_CONTEXT_TOKENS > 0
    assert settings.MAX_HISTORY_MESSAGES > 0


def test_settings_custom_env():
    """Valida a sobreposição de configurações por variáveis de ambiente."""
    with patch.dict(
        os.environ,
        {
            "APP_NAME": "ULTRON-TEST",
            "APP_ENV": "test",
            "DEFAULT_LLM_PROVIDER": "mock",
            "MAX_CONTEXT_TOKENS": "1024",
        },
    ):
        settings = Settings()
        assert settings.APP_NAME == "ULTRON-TEST"
        assert settings.APP_ENV == "test"
        assert settings.DEFAULT_LLM_PROVIDER == "mock"
        assert settings.MAX_CONTEXT_TOKENS == 1024


def test_get_settings_cache():
    """Valida que get_settings() utiliza lru_cache."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
