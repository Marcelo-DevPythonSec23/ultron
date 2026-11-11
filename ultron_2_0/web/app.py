"""HUD web do ULTRON 2.0 (Etapa 5).

Uma interface REAL sobre o MESMO `OrchestratorBridge` usado pela CLI e pela
voz: não há lógica de conversa aqui, só leitura de estado e encaminhamento de
mensagens ao núcleo. Nenhum botão é decorativo — cada endpoint faz algo:

    GET  /                HUD (HTML/CSS/JS locais, sem CDN; tema ULTRON)
    GET  /api/status      estado real (providers, tools, memória, banco, áudio)
    GET  /api/tools       contratos reais das ferramentas registradas
    GET  /api/history     mensagens persistidas pelo núcleo (conversa corrente)
    POST /api/chat        um turno pelo orquestrador do lain
    POST /api/new         encerra a conversa corrente (histórico preservado)

Por que web e não Qt (decisão nº 6 da auditoria, resolvida aqui): o ambiente
tem ~4 GB de RAM e o PyQt6 exigiria uma instalação nova pesada; FastAPI/uvicorn
já são a base do próprio lain. A interface é local (bind padrão 127.0.0.1) e
não modifica nenhum repositório original.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..voice.audio_io import audio_capabilities

logger = logging.getLogger("ultron2.web")

_STATIC_DIR = Path(__file__).resolve().parent / "static"


class ChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    provider: str | None = None


class RejectBody(BaseModel):
    reason: str = Field(default="rejected by user", max_length=200)


def _contract_dict(contract: Any) -> dict[str, Any]:
    return {
        "name": contract.name,
        "description": contract.description,
        "parameters": contract.parameters,
        "required": list(contract.required_fields),
        "timeout_seconds": contract.timeout_seconds,
        "requires_confirmation": contract.requires_confirmation,
        "permissions": list(contract.permissions),
        "source": contract.source,
        "expected_errors": list(contract.expected_errors),
    }


def create_app(
    bridge: Any,
    *,
    audio_probe: Callable[[], dict[str, Any]] = audio_capabilities,
) -> FastAPI:
    """App FastAPI ligado a um `OrchestratorBridge` já iniciado."""
    app = FastAPI(title="ULTRON 2.0", docs_url=None, redoc_url=None)
    started_at = time.time()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(html)

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        try:
            audio = audio_probe()
        except Exception as exc:  # diagnóstico nunca derruba o HUD
            audio = {"error": f"{type(exc).__name__}: {exc}"}
        return {
            **bridge.status(),
            "audio": audio,
            "web_uptime_seconds": round(time.time() - started_at, 1),
        }

    @app.get("/api/tools")
    async def tools() -> dict[str, Any]:
        gateway = getattr(bridge.runtime, "gateway", None)
        contracts = gateway.list_contracts() if gateway is not None else []
        return {"tools": [_contract_dict(c) for c in contracts]}

    @app.get("/api/history")
    async def history(limit: int = 50) -> dict[str, Any]:
        messages = await asyncio.to_thread(bridge.history, max(1, min(limit, 200)))
        return {
            "conversation_id": bridge.conversation_id,
            "messages": messages,
        }

    @app.post("/api/chat")
    async def chat(body: ChatBody) -> dict[str, Any]:
        if bridge.runtime.orchestrator is None:
            raise HTTPException(status_code=503, detail="núcleo não iniciado")
        kwargs = {"provider": body.provider} if body.provider else {}
        try:
            response = await asyncio.to_thread(
                bridge.process_text, body.message, **kwargs
            )
        except Exception as exc:
            logger.exception("falha ao processar turno pela web")
            raise HTTPException(
                status_code=502,
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc

        # Rastro de ferramentas vem do histórico persistido (ChatResponse não
        # carrega raw_metadata — contrato do lain).
        tool_calls: list[dict[str, Any]] = []
        try:
            recent = await asyncio.to_thread(bridge.history, 2)
            assistant = [m for m in recent if m["role"] == "assistant"]
            if assistant:
                tool_calls = assistant[-1].get("tool_calls", [])
        except Exception:  # histórico é diagnóstico; a resposta já está pronta
            logger.debug("não foi possível ler tool_calls do histórico")

        usage = getattr(response, "usage", None)
        return {
            "content": response.content,
            "conversation_id": response.conversation_id,
            "message_id": getattr(response, "message_id", None),
            "provider": getattr(response, "provider", None),
            "model": getattr(response, "model", None),
            "usage": {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            },
            "tool_calls": tool_calls,
        }

    @app.post("/api/new")
    async def new_conversation() -> dict[str, Any]:
        bridge.new_conversation()
        return {"conversation_id": None, "status": "new-conversation"}

    # -- autorização interativa (Fase 2 do ULTRON 2.1) ------------------------
    # O HUD é a interface que decide: o pedido fica pendente enquanto o turno
    # aguarda; aprovar/recusar aqui libera o ToolGateway. O modelo nunca vê
    # token nem chama estes endpoints.
    @app.get("/api/approvals")
    async def approvals() -> dict[str, Any]:
        return {"pending": bridge.pending_actions()}

    @app.post("/api/approvals/{action_id}/approve")
    async def approve(action_id: str) -> dict[str, Any]:
        return _decide(lambda: bridge.approve_action(action_id))

    @app.post("/api/approvals/{action_id}/reject")
    async def reject(action_id: str, body: RejectBody | None = None) -> dict[str, Any]:
        reason = body.reason if body is not None else "rejected by user"
        return _decide(lambda: bridge.reject_action(action_id, reason))

    def _decide(operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        from ..authorization import (
            AuthorizationDenied,
            AuthorizationError,
            ExpiredToken,
            TokenAlreadyUsed,
            UnknownAction,
        )

        try:
            return {"ok": True, "action": operation()}
        except UnknownAction as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ExpiredToken, TokenAlreadyUsed, AuthorizationDenied) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except AuthorizationError as exc:  # pragma: no cover - base defensiva
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


def tool_calls_summary(raw_metadata: str | None) -> list[dict[str, Any]]:
    """Utilidade de diagnóstico usada em testes/logs."""
    try:
        return json.loads(raw_metadata or "{}").get("tool_calls", []) or []
    except (ValueError, TypeError):
        return []
