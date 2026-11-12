"""Adaptador para servidores MCP (Model Context Protocol) — Fase 5.

Usa a interface real do OpenCode para gerenciar servidores MCP:
    opencode mcp list      # lista servidores configurados e status
    opencode mcp add       # adiciona um servidor
    opencode mcp auth      # autentica em servidor OAuth remoto

Não há um servidor MCP real configurado neste ambiente, portanto o adaptador
lista os servidores disponíveis e, para execução de tarefa MCP real,
reporta controladamente quando nenhum servidor está acessível — sem inventar
um protocolo MCP nem um servidor fictício.
"""

from __future__ import annotations

from typing import Any

from .base import ExternalIntegration
from .contracts import IntegrationTask, IntegrationType


class MCPAdapter(ExternalIntegration):
    """Adaptador para servidores MCP via `opencode mcp`."""

    def __init__(
        self,
        *,
        opencode_cmd: str = "opencode",
        timeout_seconds: float = 30.0,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            integration_type=IntegrationType.MCP,
            target="mcp",
            timeout_seconds=timeout_seconds,
            enabled=enabled,
            command=opencode_cmd,
        )
        self._opencode_cmd = opencode_cmd

    def build_command(self, task: IntegrationTask) -> list[str]:
        # Lista os servidores MCP configurados. Uma execução de tarefa MCP
        # real requereria um servidor ativo via stdio/HTTP; sem servidor
        # configurado, o adapter apenas lista e relata.
        return [self._opencode_cmd, "mcp", "list"]

    def parse_output(self, stdout: str) -> dict[str, Any]:
        stdout = stdout.strip()
        if not stdout:
            return {
                "summary": "nenhum servidor MCP configurado ou saída vazia",
                "servers": [],
            }
        try:
            parsed = __import__("json").loads(stdout)
        except Exception:
            return {
                "summary": stdout[:500],
                "servers": [],
                "raw": {"text": stdout},
            }

        if isinstance(parsed, dict):
            servers = parsed.get("servers") or parsed.get("mcpServers") or []
            if isinstance(servers, dict):
                servers = [
                    {"name": k, **(v if isinstance(v, dict) else {})}
                    for k, v in servers.items()
                ]
            return {
                "summary": f"{len(servers)} servidor(es) MCP listado(s)",
                "servers": servers,
                "raw": parsed,
            }
        if isinstance(parsed, list):
            return {
                "summary": f"{len(parsed)} servidor(es) MCP listado(s)",
                "servers": parsed,
                "raw": parsed,
            }
        return {
            "summary": str(parsed)[:500],
            "servers": [],
            "raw": parsed,
        }


__all__ = ["MCPAdapter"]
