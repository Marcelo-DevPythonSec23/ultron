"""Módulo de configuração centralizada do ULTRON usando Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente ou arquivo .env."""

    # Identificação da Aplicação
    APP_NAME: str = Field(default="ULTRON", description="Nome da aplicação")
    APP_ENV: Literal["development", "test", "production"] = Field(
        default="development", description="Ambiente de execução"
    )
    LOG_LEVEL: str = Field(default="INFO", description="Nível de log (DEBUG, INFO, WARNING, ERROR)")

    # Servidor HTTP
    API_HOST: str = Field(default="0.0.0.0", description="Host de bind da API")
    API_PORT: int = Field(default=8000, description="Porta de bind da API")

    # Provedor LLM Padrão
    DEFAULT_LLM_PROVIDER: str = Field(
        default="gemini", description="Identificador do provedor LLM padrão (ex: gemini, mock)"
    )
    GEMINI_API_KEY: SecretStr | None = Field(
        default=None, description="Chave de API do Google Gemini (secreta)"
    )
    GEMINI_DEFAULT_MODEL: str = Field(
        default="gemini-2.5-flash", description="Modelo padrão do Google Gemini"
    )

    # Persistência de Dados
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./ultron.db",
        description="URL de conexão assíncrona do banco de dados",
    )

    # Gestão de Histórico e Contexto
    MAX_CONTEXT_TOKENS: int = Field(
        default=4096, description="Limite máximo de tokens para compor o contexto da conversa"
    )
    MAX_HISTORY_MESSAGES: int = Field(
        default=20, description="Número máximo de mensagens históricas a recuperar por padrão"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_gemini_api_key(self) -> str | None:
        """Retorna o valor em texto puro da chave do Gemini de forma controlada."""
        return self.GEMINI_API_KEY.get_secret_value() if self.GEMINI_API_KEY else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna uma instância única em cache das configurações."""
    return Settings()
