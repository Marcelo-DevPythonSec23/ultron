"""Contratos explícitos de ferramentas do ULTRON 2.0 (master prompt §7.1).

Cada ferramenta integrada possui um contrato que reflete a implementação real:
nome, descrição, parâmetros, campos obrigatórios, resultado esperado,
exceções possíveis, permissões, requisito de confirmação, timeout e estratégia
de erro. `source` registra de qual módulo original do Mark-LVI a ferramenta veio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class ToolContract:
    """Contrato de uma ferramenta adaptada do Mark-LVI para o ULTRON."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required_fields: list[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    requires_confirmation: bool = False
    allowed_modes: list[str] = field(default_factory=lambda: ["text", "voice"])
    permissions: list[str] = field(default_factory=list)
    # De onde a implementação veio (arquivo original do Mark-LVI ou "ultron-2.0").
    source: str = ""
    # Erros conhecidos que a ferramenta pode produzir (documentação do contrato).
    expected_errors: list[str] = field(default_factory=list)

    def declaration(self) -> dict[str, Any]:
        """Declaração no formato que o loader de actions do Mark-LVI produz.

        Sem chaves internas (tier/brief) — apenas o que vai ao modelo.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass(slots=True)
class ToolResult:
    """Resultado padronizado de uma execução de ferramenta."""

    ok: bool
    tool_name: str
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        """Status no protocolo core/outcome.py do Mark-LVI."""
        if self.ok:
            return "done" if not self.metadata.get("partial") else "unverified"
        return "failed"

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool_name": self.tool_name,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }

    def render_for_model(self) -> str:
        """Resultado como fatos legíveis para o modelo (não uma frase pronta).

        Segue o princípio de core/outcome.py: entregar fatos em forma de
        máquina para que o MODELO escreva a frase, no idioma do usuário.
        """
        if not self.ok:
            reason = self.error or "unknown error"
            return (
                f"status=failed action={self.tool_name} reason=\"{reason}\" "
                "-- This did NOT happen. Tell the user so, with the reason."
            )
        payload = self.result
        if isinstance(payload, str):
            body = payload
        else:
            import json

            body = json.dumps(payload, ensure_ascii=False, default=str)
        elapsed = self.metadata.get("elapsed_seconds")
        meta = f" elapsed={elapsed:.2f}s" if isinstance(elapsed, (int, float)) else ""
        return (
            f"status={self.status} action={self.tool_name}{meta}\n{body}"
        )


# Executor canônico: recebe o dict de parâmetros, devolve str (protocolo outcome)
ToolExecutor = Callable[[dict], str]
