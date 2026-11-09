"""Ponto de entrada principal da aplicação FastAPI ULTRON."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.config import get_settings
from app.utils.logging import setup_logging

logger = logging.getLogger("ultron.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação (inicialização e encerramento)."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info("Iniciando %s no ambiente '%s'...", settings.APP_NAME, settings.APP_ENV)
    yield
    logger.info("Encerrando %s com segurança...", settings.APP_NAME)


def create_app() -> FastAPI:
    """Fábrica de criação da aplicação FastAPI com rotas e middlewares configurados."""
    settings = get_settings()

    application = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Assistente Conversacional Modular em Python",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Registrar Roteadores
    application.include_router(health_router, prefix="/api/v1")

    # Tratamento global de exceções não capturadas
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Exceção não tratada capturada: %s", str(exc), exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Ocorreu um erro interno no processamento da solicitação.",
                }
            },
        )

    return application


app = create_app()
