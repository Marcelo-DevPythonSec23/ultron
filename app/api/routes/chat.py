"""Rotas da API para envio de mensagens conversacionais e histórico."""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import ChatServiceDep, OrchestratorDep
from app.intelligence.providers.base import (
    LLMException,
    ProviderAuthenticationError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.models.conversation import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    ConversationListResponse,
)

logger = logging.getLogger("ultron.api.chat")

router = APIRouter(tags=["Conversations & Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Enviar mensagem e receber resposta do ULTRON",
)
async def send_chat_message(
    payload: ChatRequest,
    orchestrator: OrchestratorDep,
) -> ChatResponse:
    """Processa uma mensagem conversacional enviada pelo usuário."""
    try:
        response = await orchestrator.process_chat(payload)
        return response
    except ProviderAuthenticationError as exc:
        logger.warning("Falha de autenticação no provedor: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_ERROR", "message": exc.message},
        ) from exc
    except ProviderRateLimitError as exc:
        logger.warning("Limite de taxa excedido no provedor: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": exc.message},
        ) from exc
    except ProviderUnavailableError as exc:
        logger.error("Provedor de LLM indisponível: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": exc.message},
        ) from exc
    except ProviderInvalidRequestError as exc:
        logger.warning("Requisição inválida enviada ao provedor: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REQUEST", "message": exc.message},
        ) from exc
    except LLMException as exc:
        logger.error("Erro genérico na camada de inteligência: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "PROVIDER_ERROR", "message": exc.message},
        ) from exc


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="Listar conversas existentes",
)
async def list_conversations(
    chat_service: ChatServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ConversationListResponse:
    """Lista as conversas armazenadas com paginação."""
    items, total = await chat_service.list_conversations(limit=limit, offset=offset)
    return ConversationListResponse(total=total, items=items)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationHistoryResponse,
    summary="Recuperar mensagens de uma conversa",
)
async def get_conversation_messages(
    conversation_id: str,
    chat_service: ChatServiceDep,
) -> ConversationHistoryResponse:
    """Recupera o histórico completo de mensagens de uma conversa específica."""
    messages = await chat_service.get_conversation_history_items(conversation_id)
    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        messages=messages,
    )
