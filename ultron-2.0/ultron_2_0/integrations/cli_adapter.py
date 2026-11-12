"""Adaptador CLI para agentes externos (OpenCode) — Fase 5.

Envolve o comando real `opencode run` como subprocesso isolado, com timeout,
parse de saída JSON (`--format json`) e sanitização de credenciais.

Interface real confirmada:
    opencode run [--session ID] [--model MODEL] [--agent AGENT] [--auto]
                 [--format json] <message>

Não inventa comandos nem contratos: usa apenas o que o OpenCode expõe.
"""

from __future__ import annotations

from typing import Any

from .base import ExternalIntegration, sanitize_output
from .contracts import IntegrationTask, IntegrationType


class OpenCodeAdapter(ExternalIntegration):
    """Adaptador para o agente CLI OpenCode."""

    def __init__(
        self,
        *,
        opencode_cmd: str = "opencode",
        timeout_seconds: float = 120.0,
        enabled: bool = True,
        default_session: str | None = None,
        default_model: str | None = None,
        auto_approve: bool = False,
    ) -> None:
        super().__init__(
            integration_type=IntegrationType.CLI,
            target="opencode",
            timeout_seconds=timeout_seconds,
            enabled=enabled,
            command=opencode_cmd,
        )
        self._default_session = default_session
        self._default_model = default_model
        self._auto_approve = auto_approve

    def build_command(self, task: IntegrationTask) -> list[str]:
        cmd = [self.command, "run", "--format", "json"]
        if task.params.get("session") or self._default_session:
            cmd += ["--session", str(task.params.get("session") or self._default_session)]
        if task.params.get("model") or self._default_model:
            cmd += ["--model", str(task.params.get("model") or self._default_model)]
        if task.params.get("agent"):
            cmd += ["--agent", str(task.params["agent"])]
        if self._auto_approve or task.params.get("auto_approve"):
            cmd.append("--auto")
        # A mensagem vem por argumento posicional (ou stdin no futuro).
        cmd.append(task.prompt)
        return cmd

    def parse_output(self, stdout: str) -> dict[str, Any]:
        """Analisa a saída JSON do `opencode run --format json`.

        Se não for JSON válido, trata o texto bruto como conteúdo (sem
        inventar estrutura). A saída é sanitizada antes de retornar.
        """
        stdout = stdout.strip()
        if not stdout:
            return {"summary": "saída vazia do OpenCode", "text": ""}

        # Tenta parsear como JSON (uma linha ou múltiplas).
        parsed: Any = None
        try:
            parsed = __import__("json").loads(stdout)
        except Exception:
            # Talvez seja NDJSON (uma linha por evento). Tenta a última linha.
            lines = [l for l in stdout.splitlines() if l.strip()]
            if lines:
                try:
                    parsed = __import__("json").loads(lines[-1])
                except Exception:
                    parsed = None

        if isinstance(parsed, dict):
            summary = parsed.get("summary") or parsed.get("text") or ""
            if not summary:
                summary = str(parsed)[:500]
            return {
                "summary": sanitize_output(summary, max_chars=1000),
                "text": sanitize_output(str(parsed.get("text", "")), max_chars=2000),
                "raw": parsed,
            }
        # Não é JSON: devolve o texto bruto sanitizado.
        return {
            "summary": sanitize_output(stdout[:500]),
            "text": sanitize_output(stdout[:2000]),
            "raw": {"text": stdout},
        }


__all__ = ["OpenCodeAdapter"]
