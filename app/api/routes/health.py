"""Endpoint de verificação de integridade e saúde da aplicação (Health Check)."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.dependencies import SettingsDep

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Modelo de resposta para o status de saúde do ULTRON."""

    status: str = Field(..., examples=["healthy"])
    app_name: str = Field(..., examples=["ULTRON"])
    version: str = Field(default="0.1.0")
    environment: str = Field(..., examples=["development"])
    active_provider: str = Field(..., examples=["gemini"])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)


@router.get("/health", response_model=HealthResponse)
async def get_health(settings: SettingsDep) -> HealthResponse:
    """Retorna o status operacional da aplicação ULTRON."""
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version="0.1.0",
        environment=settings.APP_ENV,
        active_provider=settings.DEFAULT_LLM_PROVIDER,
        timestamp=datetime.now(UTC),
        details={
            "gemini_configured": settings.GEMINI_API_KEY is not None,
            "database_url": settings.DATABASE_URL.split("///")[-1],  # nome seguro sem credenciais
        },
    )
