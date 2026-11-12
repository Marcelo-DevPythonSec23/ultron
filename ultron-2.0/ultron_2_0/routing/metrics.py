"""Métricas por provedor e cooldown — observabilidade sem credenciais.

O roteador registra chamadas, sucessos, falhas, retries, latência e o último
erro de cada provedor. Erros passam por sanitização: nada que pareça chave,
token ou segredo entra no snapshot exposto ao CLI/HUD.

Cooldown: ao falhar, o provedor fica indisponível por `cooldown_seconds`.
Isso evita insistir num provedor derrubado a cada turno; a política de
seleção ignora provedores em cooldown (o primário ainda pode ser tentado se
for a única opção, por decisão explícita do roteador).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

_MAX_ERROR_CHARS = 300

# Padrões de segredo conhecidos (defesa em profundidade; erros já deveriam vir
# sanitizados da camada de provider).
_SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_\-]{16,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{10,}"),
    re.compile(
        r"\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*\s*[=:]\s*\S+",
        re.IGNORECASE,
    ),
)


def sanitize_error(text: str | None) -> str | None:
    """Remove segredos e limita o tamanho de uma mensagem de erro."""
    if text is None:
        return None
    value = str(text)
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[redacted]", value)
    return value[:_MAX_ERROR_CHARS]


@dataclass
class ProviderMetrics:
    """Contadores observáveis de um provedor."""

    provider_id: str
    calls: int = 0
    successes: int = 0
    failures: int = 0
    retries: int = 0
    consecutive_failures: int = 0
    total_latency_seconds: float = 0.0
    last_latency_seconds: float | None = None
    last_error_type: str | None = None
    last_error: str | None = None
    cooldown_until: float = 0.0
    call_history: list[float] = field(default_factory=list)

    def public(self, *, now: float | None = None) -> dict:
        current = time.monotonic() if now is None else now
        remaining = max(0.0, self.cooldown_until - current)
        return {
            "provider_id": self.provider_id,
            "calls": self.calls,
            "successes": self.successes,
            "failures": self.failures,
            "retries": self.retries,
            "consecutive_failures": self.consecutive_failures,
            "last_latency_seconds": (
                round(self.last_latency_seconds, 4)
                if self.last_latency_seconds is not None
                else None
            ),
            "average_latency_seconds": (
                round(self.total_latency_seconds / self.successes, 4)
                if self.successes
                else None
            ),
            "last_error_type": self.last_error_type,
            "last_error": self.last_error,
            "available": remaining <= 0.0,
            "cooldown_remaining_seconds": round(remaining, 2),
        }


class MetricsRegistry:
    """Coleção de `ProviderMetrics` indexada por `provider_id`."""

    def __init__(self, *, clock=time.monotonic) -> None:
        self._clock = clock
        self._entries: dict[str, ProviderMetrics] = {}

    def entry(self, provider_id: str) -> ProviderMetrics:
        return self._entries.setdefault(provider_id, ProviderMetrics(provider_id))

    # -- eventos --------------------------------------------------------------
    def record_call(self, provider_id: str) -> None:
        self.entry(provider_id).calls += 1

    def record_retry(self, provider_id: str) -> None:
        self.entry(provider_id).retries += 1

    def record_success(self, provider_id: str, latency_seconds: float) -> None:
        entry = self.entry(provider_id)
        latency = max(0.0, float(latency_seconds))
        entry.successes += 1
        entry.consecutive_failures = 0
        entry.cooldown_until = 0.0
        entry.last_latency_seconds = latency
        entry.total_latency_seconds += latency

    def record_failure(self, provider_id: str, error: BaseException, *, cooldown_seconds: float) -> None:
        entry = self.entry(provider_id)
        entry.failures += 1
        entry.consecutive_failures += 1
        entry.last_error_type = type(error).__name__
        entry.last_error = sanitize_error(str(error))
        if cooldown_seconds > 0:
            entry.cooldown_until = self._clock() + float(cooldown_seconds)

    # -- consulta -------------------------------------------------------------
    def available(self, provider_id: str, *, now: float | None = None) -> bool:
        entry = self._entries.get(provider_id)
        if entry is None:
            return True
        current = self._clock() if now is None else now
        return entry.cooldown_until <= current

    def reset(self, provider_id: str) -> None:
        self._entries.pop(provider_id, None)

    def public(self, *, now: float | None = None) -> dict[str, dict]:
        current = self._clock() if now is None else now
        return {
            provider_id: entry.public(now=current)
            for provider_id, entry in self._entries.items()
        }
