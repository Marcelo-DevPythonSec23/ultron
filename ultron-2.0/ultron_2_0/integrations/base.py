"""Classe base para integrações externas (Fase 5).

Uma integração envolve um processo/serviço externo (agente CLI ou servidor
MCP) como subprocesso isolado, com timeout, parse de saída estruturada e
sanitização de credenciais. Falhas nunca comprometem o núcleo ULTRON.

Não inventa comandos, APIs ou contratos: usa apenas a interface real de cada
ferramenta externa (AGENTS.md §4.4).
"""

from __future__ import annotations

import asyncio
import logging
import re
import shlex
from typing import Any

from .contracts import IntegrationResult, IntegrationType

logger = logging.getLogger("ultron2.integrations.base")

# Padrões de segredo para sanitizar saídas de processos externos.
_SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_\-]{16,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{10,}"),
    re.compile(
        r"\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*\s*[=:]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),  # possíveis tokens longos
)


def sanitize_output(text: str | None, *, max_chars: int = 2000) -> str | None:
    """Remove segredos e limita o tamanho da saída de um processo externo."""
    if text is None:
        return None
    value = str(text)
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[redacted]", value)
    return value[:max_chars]


class ExternalIntegration:
    """Contrato base de uma integração externa.

    Subclasses implementam `build_command(task)` e `parse_output(stdout)`.
    O método `run(task)` executa o processo isolado com timeout e devolve
    um `IntegrationResult`.
    """

    def __init__(
        self,
        integration_type: IntegrationType,
        target: str,
        *,
        timeout_seconds: float = 60.0,
        enabled: bool = True,
        command: str | None = None,
    ) -> None:
        self.integration_type = integration_type
        self.target = target
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self.enabled = enabled
        self.command = command  # comando base, se houver (ex: "opencode")

    def is_enabled(self) -> bool:
        return self.enabled

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    # -- contrato obrigatório -------------------------------------------------
    def build_command(self, task) -> list[str]:
        """Constrói a lista de argumentos do subprocesso (sem shell=True)."""
        raise NotImplementedError

    def parse_output(self, stdout: str) -> dict[str, Any]:
        """Analisa a saída bruta do processo em um dicionário estruturado."""
        raise NotImplementedError

    # -- execução isolada -----------------------------------------------------
    async def run(self, task) -> IntegrationResult:
        """Executa o comando externo como subprocesso com timeout.

        Nunca usa shell=True; argumentos são passados como lista. Timeout é
        aplicado com asyncio.wait_for. Saída é sanitizada (sem credenciais).
        """
        if not self.enabled:
            return IntegrationResult(
                task_id=task.id,
                integration_type=self.integration_type,
                target=self.target,
                success=False,
                error=f"integração '{self.target}' desabilitada",
                summary="integração desabilitada pelo operador",
            )

        cmd = self.build_command(task)
        started = asyncio.get_event_loop().time()
        logger.info(
            "integração %s executando %s (timeout=%.1fs)",
            self.target,
            " ".join(shlex.quote(c) for c in cmd),
            self.timeout_seconds,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.wait()
                elapsed = asyncio.get_event_loop().time() - started
                return IntegrationResult(
                    task_id=task.id,
                    integration_type=self.integration_type,
                    target=self.target,
                    success=False,
                    error=f"timeout após {self.timeout_seconds:g}s",
                    summary="execução interrompida por timeout",
                    execution_seconds=round(elapsed, 4),
                )

            elapsed = asyncio.get_event_loop().time() - started
            stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

            if proc.returncode != 0:
                return IntegrationResult(
                    task_id=task.id,
                    integration_type=self.integration_type,
                    target=self.target,
                    success=False,
                    error=f"processo saiu com código {proc.returncode}: "
                    f"{sanitize_output(stderr_text, max_chars=500)}",
                    summary="processo externo falhou",
                    raw_output=sanitize_output(stdout_text),
                    execution_seconds=round(elapsed, 4),
                )

            parsed = self.parse_output(stdout_text)
            return IntegrationResult(
                task_id=task.id,
                integration_type=self.integration_type,
                target=self.target,
                success=True,
                content=parsed,
                summary=parsed.get("summary", "") if isinstance(parsed, dict) else "",
                raw_output=sanitize_output(stdout_text),
                execution_seconds=round(elapsed, 4),
            )

        except FileNotFoundError:
            elapsed = asyncio.get_event_loop().time() - started
            return IntegrationResult(
                task_id=task.id,
                integration_type=self.integration_type,
                target=self.target,
                success=False,
                error=f"comando não encontrado: {cmd[0]}",
                summary="executável externo não instalado",
                execution_seconds=round(elapsed, 4),
            )
        except Exception as exc:  # noqa: BLE001 — falha externa não derruba o núcleo
            elapsed = asyncio.get_event_loop().time() - started
            logger.exception("integração %s falhou: %s", self.target, exc)
            return IntegrationResult(
                task_id=task.id,
                integration_type=self.integration_type,
                target=self.target,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                summary="execução interrompida por exceção",
                execution_seconds=round(elapsed, 4),
            )

    def public(self) -> dict[str, Any]:
        return {
            "type": self.integration_type.value,
            "target": self.target,
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
            "command": self.command,
        }
