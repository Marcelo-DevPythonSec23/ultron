"""Gateway de execução de ferramentas do ULTRON 2.0 (master prompt §7.1/§7.2).

Camada entre a decisão do MODELO (feito no tool_loop) e as actions do Mark-LVI:

    decisão do modelo
        -> validação do contrato (campos obrigatórios, tipos, chaves permitidas)
        -> verificação de permissão/confirmação (gate para ações destrutivas)
        -> execução autorizada (worker thread + timeout, nunca no event loop)
        -> resultado padronizado (ToolResult, protocolo core/outcome)

As actions do Mark-LVI são síncronas e rodam em worker threads por design
(Mark-LVI-main/AGENTS.md); o orquestrador do ULTRON é asyncio. A ponte é
`asyncio.to_thread` com `asyncio.wait_for` — o event loop nunca bloqueia e toda
ferramenta tem um teto de tempo.

Nenhuma ferramenta é executada sem contrato registrado (allowlist). Ferramentas
com `requires_confirmation=True` são recusadas enquanto não houver uma
confirmação explícita de interface ligada (gate do core/confirm.py do Mark-LVI,
integrado em etapa posterior) — recusar é o comportamento seguro.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .tool_contracts import ToolContract, ToolExecutor, ToolResult

logger = logging.getLogger("ultron2.tools.gateway")
audit = logging.getLogger("ultron2.tools.audit")

# Tipos do esquema de declaração do Mark-LVI -> validadores Python.
_TYPE_CHECKS: dict[str, tuple[type, ...]] = {
    "STRING": (str,),
    "NUMBER": (int, float),
    "INTEGER": (int,),
    "BOOLEAN": (bool,),
    "ARRAY": (list,),
    "OBJECT": (dict,),
}


def _coerce(value: Any, expected: str) -> Any:
    """Coerções conservadoras para erros triviais de JSON de modelo.

    int/float para STRING e "3"/"true" para NUMBER/BOOLEAN são erros comuns de
    modelo; qualquer coisa que não seja trivialemente coerível levanta
    ValueError e vira um resultado de validação falho (não uma exceção solta).
    """
    if expected == "STRING" and isinstance(value, (int, float)):
        return str(value)
    if expected in ("NUMBER", "INTEGER") and isinstance(value, str):
        stripped = value.strip()
        try:
            return int(stripped) if expected == "INTEGER" else float(stripped)
        except ValueError as exc:
            raise ValueError(f"cannot parse '{value}' as {expected}") from exc
    if expected == "BOOLEAN" and isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "false"):
            return lowered == "true"
        raise ValueError(f"cannot parse '{value}' as BOOLEAN")
    checks = _TYPE_CHECKS.get(expected)
    if checks and not isinstance(value, checks):
        raise ValueError(f"expected {expected}, got {type(value).__name__}")
    return value


class ToolGateway:
    """Registro + validação + execução das ferramentas integradas."""

    def __init__(self) -> None:
        self._contracts: dict[str, ToolContract] = {}
        self._executors: dict[str, ToolExecutor] = {}

    # -- registro -----------------------------------------------------------
    def register(self, contract: ToolContract, executor: ToolExecutor) -> None:
        if not contract.name:
            raise ValueError("contrato sem nome")
        if contract.name in self._contracts:
            raise ValueError(f"ferramenta duplicada: {contract.name}")
        self._contracts[contract.name] = contract
        self._executors[contract.name] = executor
        logger.info(
            "Ferramenta registrada: %s (fonte=%s, timeout=%.1fs, confirmação=%s)",
            contract.name,
            contract.source or "?",
            contract.timeout_seconds,
            contract.requires_confirmation,
        )

    def has(self, name: str) -> bool:
        return name in self._contracts

    def get_contract(self, name: str) -> ToolContract | None:
        return self._contracts.get(name)

    def list_contracts(self) -> list[ToolContract]:
        return list(self._contracts.values())

    def names(self) -> list[str]:
        return sorted(self._contracts.keys())

    def declarations(self) -> list[dict[str, Any]]:
        """Declarações no formato de TOOL do Mark-LVI (para schema.to_prompt)."""
        return [c.declaration() for c in self._contracts.values()]

    # -- validação ----------------------------------------------------------
    def validate(self, name: str, parameters: dict | None) -> tuple[dict | None, str | None]:
        """Valida parâmetros contra o contrato. Retorna (params, erro)."""
        contract = self._contracts.get(name)
        if contract is None:
            known = ", ".join(self.names()) or "(none)"
            return None, f"unknown tool '{name}'. Available tools: {known}"

        params = dict(parameters or {})
        properties = (contract.parameters or {}).get("properties", {})

        # 1. Campos obrigatórios presentes e não vazios.
        for field_name in contract.required_fields:
            value = params.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                return None, f"missing required parameter '{field_name}' for tool '{name}'"

        # 2. Tipos coeridos; opcionais ausentes/Nones são removidos.
        validated: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            spec = properties.get(key)
            if spec is None:
                allowed = ", ".join(sorted(properties)) or "(none)"
                return None, (
                    f"unknown parameter '{key}' for tool '{name}'. "
                    f"Allowed parameters: {allowed}"
                )
            expected = str(spec.get("type", "STRING")).upper()
            try:
                validated[key] = _coerce(value, expected)
            except ValueError as exc:
                return None, f"invalid parameter '{key}' for tool '{name}': {exc}"

        return validated, None

    # -- execução ------------------------------------------------------------
    async def execute(self, name: str, parameters: dict | None) -> ToolResult:
        """Executa uma ferramenta com validação, timeout e auditoria."""
        params, error = self.validate(name, parameters)
        if error is not None:
            audit.warning("tool=%s rejected=validation error=%s", name, error)
            return ToolResult(ok=False, tool_name=name, error=error)

        contract = self._contracts[name]
        if contract.requires_confirmation:
            # Gate de confirmação (core/confirm.py) ainda não ligado à
            # interface do 2.0: recusar é o único comportamento seguro.
            reason = (
                "this tool requires explicit user confirmation, which is not "
                "available in this interface yet"
            )
            audit.warning("tool=%s rejected=confirmation-required", name)
            return ToolResult(ok=False, tool_name=name, error=reason)

        executor = self._executors[name]
        audit.info(
            "tool=%s params=%s timeout=%.1fs",
            name,
            {k: v for k, v in (params or {}).items()},
            contract.timeout_seconds,
        )
        try:
            outcome = await asyncio.wait_for(
                asyncio.to_thread(executor, params or {}),
                timeout=contract.timeout_seconds,
            )
        except asyncio.TimeoutError:
            audit.error("tool=%s status=timeout limit=%.1fs", name, contract.timeout_seconds)
            return ToolResult(
                ok=False,
                tool_name=name,
                error=f"tool '{name}' timed out after {contract.timeout_seconds:.0f}s",
                metadata={"timeout_seconds": contract.timeout_seconds},
            )
        except Exception as exc:  # ferramentas nunca derrubam o loop
            audit.exception("tool=%s status=crashed", name)
            return ToolResult(ok=False, tool_name=name, error=f"{type(exc).__name__}: {exc}")

        rendered = "" if outcome is None else str(outcome)
        audit.info("tool=%s status=ok bytes=%d", name, len(rendered))
        return ToolResult(
            ok=True,
            tool_name=name,
            result=rendered,
            metadata={"source": contract.source},
        )
