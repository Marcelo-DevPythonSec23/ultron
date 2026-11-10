"""Ponto de entrada principal da aplicação FastAPI ULTRON."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.config import get_settings
from app.database.connection import init_db
from app.utils.logging import setup_logging

logger = logging.getLogger("ultron.main")
FRONTEND_PATH = Path(__file__).parent / "static" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação (inicialização e encerramento)."""
    settings = get_settings()
    setup_logging(
        settings.LOG_LEVEL,
        secrets=[settings.get_gemini_api_key()],
    )
    logger.info("Iniciando %s no ambiente '%s'...", settings.APP_NAME, settings.APP_ENV)

    # Inicializar banco de dados e tabelas
    await init_db()

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
    application.include_router(chat_router, prefix="/api/v1")

    @application.get("/", include_in_schema=False)
    async def serve_frontend() -> FileResponse:
        """Serve the local ULTRON web interface from the same origin as the API."""
        return FileResponse(FRONTEND_PATH, media_type="text/html")

    # Tratamento de exceções HTTP da aplicação
    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            code = detail.get("code", "HTTP_ERROR")
            message = detail.get("message", str(detail))
            details = detail.get("details", None)
        else:
            code = "HTTP_ERROR"
            message = str(detail)
            details = None

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                }
            },
        )

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
