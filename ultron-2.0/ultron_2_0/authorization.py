"""Autorização interativa de ações sensíveis (AGENTS.md 2.1, Fase 2).

O modelo PROPÕE uma ferramenta; quem autoriza é a INTERFACE (CLI/HUD), nunca o
modelo. O fluxo é deliberadamente separado em três etapas:

    pedido        -> `request()` cria um PendingAction com token aleatório,
                     vinculado à ferramenta e ao hash dos argumentos exatos;
    decisão       -> `approve()`/`reject()` vêm da interface (ou do handler
                     interativo da CLI). O modelo não tem acesso a este objeto;
    execução      -> `consume()` valida token, expiração e fingerprint e marca
                     o token como usado. Só então o ToolGateway executa.

Propriedades de segurança implementadas aqui:

* token de uso único (segundo `consume` falha com `TokenAlreadyUsed`);
* expiração (`ExpiredToken`) e limpeza de pendências vencidas;
* vínculo com ferramenta + argumentos (`ArgumentsMismatch` se mudarem);
* estado por ação com `threading.Event`, seguro para CLI (thread do REPL) e
  HUD (uvicorn) ao mesmo tempo;
* auditoria de pedido, aprovação, recusa, expiração e consumo sem registrar o
  token nem conteúdo sensível;
* `pending()` expõe apenas dados públicos (sem token), para a interface.

Limite conhecido: pendências vivem em memória. Reiniciar o processo descarta
tudo — o que é o comportamento seguro (nada é aprovado por sobrevivência).
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

audit = logging.getLogger("ultron2.security.authorization")

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
EXPIRED = "expired"
CONSUMED = "consumed"
CANCELLED = "cancelled"


class AuthorizationError(Exception):
    """Base de todas as falhas de autorização."""


class UnknownAction(AuthorizationError):
    """Token/action_id inexistente ou já descartado."""


class ExpiredToken(AuthorizationError):
    """A ação venceu antes de ser aprovada/consumida."""


class TokenAlreadyUsed(AuthorizationError):
    """Token já consumido (replay)."""


class ArgumentsMismatch(AuthorizationError):
    """Ferramenta ou argumentos diferentes dos autorizados."""


class AuthorizationDenied(AuthorizationError):
    """A interface recusou explicitamente a ação."""


class ActionNotApproved(AuthorizationError):
    """Tentativa de consumir sem aprovação."""


def fingerprint(tool_name: str, arguments: dict[str, Any] | None) -> str:
    """Hash estável de ferramenta + argumentos (ordem de chaves irrelevante)."""
    payload = json.dumps(
        {"tool": tool_name, "args": arguments or {}},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class PendingAction:
    """Pedido de autorização. `token` só circula dentro do processo/interface."""

    action_id: str
    token: str
    tool_name: str
    arguments: dict[str, Any]
    fingerprint: str
    created_at: float
    expires_at: float
    status: str = PENDING
    reason: str = ""
    decided_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def public(self) -> dict[str, Any]:
        """Visão para a interface: sem token, sem segredo."""
        return {
            "action_id": self.action_id,
            "tool": self.tool_name,
            "arguments": self.arguments,
            "status": self.status,
            "reason": self.reason,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "seconds_remaining": round(max(0.0, self.expires_at - time.monotonic()), 1),
        }


class _Entry:
    __slots__ = ("action", "decided")

    def __init__(self, action: PendingAction) -> None:
        self.action = action
        self.decided = threading.Event()


ConfirmationHandler = Callable[[PendingAction], bool]


class AuthorizationManager:
    """Registro thread-safe de pedidos de autorização."""

    def __init__(
        self,
        *,
        default_ttl_seconds: float = 120.0,
        clock: Callable[[], float] = time.monotonic,
        confirm_handler: ConfirmationHandler | None = None,
    ) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds deve ser > 0")
        self._ttl = float(default_ttl_seconds)
        self._clock = clock
        self._confirm_handler = confirm_handler
        self._lock = threading.RLock()
        self._by_token: dict[str, _Entry] = {}
        self._by_id: dict[str, _Entry] = {}

    # -- configuração ---------------------------------------------------------
    @property
    def has_confirmation_handler(self) -> bool:
        return self._confirm_handler is not None

    def set_confirmation_handler(self, handler: ConfirmationHandler | None) -> None:
        """Define o handler interativo (CLI). O HUD usa `approve/reject` externos."""
        self._confirm_handler = handler

    # -- pedido ---------------------------------------------------------------
    def request(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None,
        *,
        reason: str = "",
        ttl_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PendingAction:
        if not tool_name:
            raise ValueError("tool_name vazio")
        ttl = self._ttl if ttl_seconds is None else float(ttl_seconds)
        if ttl <= 0:
            raise ValueError("ttl_seconds deve ser > 0")
        now = self._clock()
        action = PendingAction(
            action_id=secrets.token_hex(8),
            token=secrets.token_urlsafe(32),
            tool_name=tool_name,
            arguments=dict(arguments or {}),
            fingerprint=fingerprint(tool_name, arguments),
            created_at=now,
            expires_at=now + ttl,
            reason=reason,
            metadata=dict(metadata or {}),
        )
        entry = _Entry(action)
        with self._lock:
            self._expire_locked()
            self._by_token[action.token] = entry
            self._by_id[action.action_id] = entry
        audit.info(
            "authorization requested action=%s tool=%s ttl=%.0fs",
            action.action_id,
            tool_name,
            ttl,
        )
        return action

    # -- decisão --------------------------------------------------------------
    def approve(self, token_or_id: str) -> PendingAction:
        return self._decide(token_or_id, APPROVED)

    def reject(self, token_or_id: str, *, reason: str = "rejected by user") -> PendingAction:
        action = self._decide(token_or_id, REJECTED)
        action.reason = reason
        return action

    def cancel(self, token_or_id: str, *, reason: str = "cancelled") -> PendingAction:
        action = self._decide(token_or_id, CANCELLED)
        action.reason = reason
        return action

    def _decide(self, token_or_id: str, status: str) -> PendingAction:
        with self._lock:
            entry = self._entry_locked(token_or_id)
            action = entry.action
            if action.status == CONSUMED:
                raise TokenAlreadyUsed(f"action {action.action_id} já foi consumida")
            if action.status in (REJECTED, CANCELLED):
                raise AuthorizationDenied(f"action {action.action_id} já foi {action.status}")
            if action.status == EXPIRED or self._clock() >= action.expires_at:
                self._mark_expired_locked(entry)
                raise ExpiredToken(f"action {action.action_id} expirou")
            if action.status == APPROVED and status == APPROVED:
                return action
            action.status = status
            action.decided_at = self._clock()
            entry.decided.set()
        audit.info("authorization %s action=%s tool=%s", status, action.action_id, action.tool_name)
        return action

    # -- consumo (antes da execução) -----------------------------------------
    def consume(
        self,
        token: str,
        tool_name: str,
        arguments: dict[str, Any] | None,
    ) -> PendingAction:
        with self._lock:
            entry = self._entry_locked(token, by_token_only=True)
            action = entry.action
            if action.status == CONSUMED:
                raise TokenAlreadyUsed(f"action {action.action_id} já foi consumida")
            if action.status == REJECTED or action.status == CANCELLED:
                raise AuthorizationDenied(f"action {action.action_id} foi {action.status}")
            if action.status == EXPIRED or self._clock() >= action.expires_at:
                self._mark_expired_locked(entry)
                raise ExpiredToken(f"action {action.action_id} expirou")
            if action.status != APPROVED:
                raise ActionNotApproved(f"action {action.action_id} ainda não foi aprovada")
            if action.tool_name != tool_name or action.fingerprint != fingerprint(
                tool_name, arguments
            ):
                audit.warning(
                    "authorization mismatch action=%s expected_tool=%s got_tool=%s",
                    action.action_id,
                    action.tool_name,
                    tool_name,
                )
                raise ArgumentsMismatch(
                    f"argumentos/ferramenta diferentes dos autorizados em {action.action_id}"
                )
            action.status = CONSUMED
        audit.info("authorization consumed action=%s tool=%s", action.action_id, tool_name)
        return action

    # -- fluxo completo (gateway) --------------------------------------------
    def request_and_wait(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None,
        *,
        reason: str = "",
        ttl_seconds: float | None = None,
        timeout_seconds: float | None = None,
    ) -> PendingAction:
        """Cria o pedido, espera a decisão e devolve a ação consumida.

        Com `confirm_handler` (CLI interativa), a decisão é síncrona. Sem ele
        (HUD), espera `approve()`/`reject()` de outra thread até expirar.
        """
        action = self.request(
            tool_name, arguments, reason=reason, ttl_seconds=ttl_seconds
        )
        with self._lock:
            entry = self._entry_locked(action.token, by_token_only=True)

        if self._confirm_handler is not None:
            try:
                approved = bool(self._confirm_handler(action))
            except Exception:  # handler de interface nunca derruba o núcleo
                audit.exception("authorization handler crashed action=%s", action.action_id)
                approved = False
            if approved:
                self.approve(action.token)
            else:
                try:
                    self.reject(action.token)
                except AuthorizationError:
                    pass
        else:
            wait_for = (
                action.expires_at - self._clock()
                if timeout_seconds is None
                else min(timeout_seconds, action.expires_at - self._clock())
            )
            entry.decided.wait(timeout=max(0.0, wait_for))

        with self._lock:
            if action.status == PENDING:
                self._mark_expired_locked(entry)
                raise ExpiredToken(
                    f"action {action.action_id} expirou sem decisão da interface"
                )
        return self.consume(action.token, tool_name, arguments)

    # -- consulta pública -----------------------------------------------------
    def pending(self) -> list[dict[str, Any]]:
        """Pendências visíveis para a interface (sem tokens)."""
        with self._lock:
            self._expire_locked()
            return [
                entry.action.public()
                for entry in self._by_id.values()
                if entry.action.status == PENDING
            ]

    def get(self, action_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._expire_locked()
            entry = self._by_id.get(action_id)
            return entry.action.public() if entry else None

    def expire_now(self) -> int:
        with self._lock:
            return self._expire_locked()

    # -- internos -------------------------------------------------------------
    def _entry_locked(self, token_or_id: str, *, by_token_only: bool = False) -> _Entry:
        entry = self._by_token.get(token_or_id)
        if entry is None and not by_token_only:
            entry = self._by_id.get(token_or_id)
        if entry is None:
            raise UnknownAction("autorização inexistente ou já descartada")
        return entry

    def _mark_expired_locked(self, entry: _Entry) -> None:
        if entry.action.status == PENDING:
            entry.action.status = EXPIRED
            entry.action.reason = "expired"
            audit.warning("authorization expired action=%s", entry.action.action_id)
        entry.decided.set()

    def _expire_locked(self) -> int:
        now = self._clock()
        count = 0
        for entry in list(self._by_id.values()):
            if entry.action.status == PENDING and now >= entry.action.expires_at:
                self._mark_expired_locked(entry)
                count += 1
        return count
