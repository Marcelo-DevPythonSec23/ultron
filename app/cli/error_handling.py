"""Classificação, sanitização e registro centralizado de erros da CLI."""

import asyncio
import errno
import json
import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from app.intelligence.providers.base import (
    LLMException,
    ProviderAccessDeniedError,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderInvalidRequestError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.utils.logging import SensitiveDataFilter


class ErrorCategory(StrEnum):
    """Categorias apresentáveis para falhas conhecidas da aplicação."""

    RESOURCE_EXHAUSTED = "RESOURCE EXHAUSTED"
    AUTHENTICATION_FAILED = "AUTHENTICATION FAILED"
    ACCESS_DENIED = "ACCESS DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE NOT FOUND"
    PROVIDER_ERROR = "PROVIDER ERROR"
    SERVICE_UNAVAILABLE = "SERVICE UNAVAILABLE"
    REQUEST_TIMEOUT = "REQUEST TIMEOUT"
    CONNECTION_FAILURE = "CONNECTION FAILURE"
    RESPONSE_ERROR = "RESPONSE ERROR"
    INVALID_REQUEST = "INVALID REQUEST"
    UNKNOWN = "UNKNOWN SYSTEM ERROR"


@dataclass(frozen=True)
class ErrorPresentation:
    """Informações seguras para mostrar ao usuário e registrar para diagnóstico."""

    category: ErrorCategory
    title: str
    message: str
    provider: str
    http_status: int | None
    status: str
    retry_message: str | None
    source: str
    details: str
    request_id: str | None


_RETRY_SECONDS = re.compile(
    r"(?:retry(?:\s+after|Delay)?|retry in)[^0-9]{0,20}"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|milliseconds?|s|seconds?|m|minutes?|h|hours?)",
    re.IGNORECASE,
)
_RETRY_CLOCK = re.compile(
    r"retry in\s+(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?"
    r"(?:(?P<s>\d+(?:\.\d+)?)s)?",
    re.IGNORECASE,
)


def sanitize_error_text(value: str) -> str:
    """Remove credenciais e credenciais incorporadas em mensagens/JSON do SDK."""
    masked = SensitiveDataFilter.mask_sensitive_text(value)
    masked = re.sub(
        r"(?i)(https?://)[^\s/@:]+:[^\s/@]+@",
        r"\1[MASCARADO]@",
        masked,
    )
    return masked


def classify_error(
    exc: BaseException,
    *,
    provider: str | None = None,
) -> ErrorPresentation:
    """Classifica exceções pelo tipo e metadados SDK sem expor o texto original."""
    root = _root_cause(exc)
    raw_details = sanitize_error_text(str(root))
    technical_details = getattr(exc, "details", None) or getattr(root, "details", None)
    if technical_details:
        raw_details = sanitize_error_text(f"{raw_details} | {technical_details}")
    http_status = _http_status(exc) or _http_status(root)
    provider_name = _provider_name(
        provider or getattr(exc, "provider", None) or getattr(root, "provider", None)
    )
    retry_after = _retry_after_seconds(exc, root)
    text = " ".join(
        (
            raw_details,
            str(getattr(exc, "details", "") or ""),
            str(getattr(root, "details", "") or ""),
        )
    ).lower()

    if http_status == 429 or isinstance(exc, ProviderRateLimitError):
        quota_kind = _quota_kind(text)
        retry = _format_retry(retry_after)
        return _presentation(
            ErrorCategory.RESOURCE_EXHAUSTED,
            "RESOURCE LIMIT",
            "O limite de utilização da API foi atingido.",
            provider_name,
            http_status,
            quota_kind,
            retry or "Consulte a disponibilidade da quota antes de tentar novamente.",
            exc,
            raw_details,
        )
    if http_status == 401 or isinstance(exc, ProviderAuthenticationError):
        return _presentation(
            ErrorCategory.AUTHENTICATION_FAILED,
            "AUTHENTICATION FAILURE",
            "As credenciais do provedor foram rejeitadas.",
            provider_name,
            http_status,
            "CREDENTIALS REJECTED",
            None,
            exc,
            raw_details,
        )
    if http_status == 403 or isinstance(exc, ProviderAccessDeniedError):
        return _presentation(
            ErrorCategory.ACCESS_DENIED,
            "ACCESS DENIED",
            "O provedor não autorizou o acesso ao recurso solicitado.",
            provider_name,
            http_status,
            "ACCESS DENIED",
            None,
            exc,
            raw_details,
        )
    if http_status == 404 or isinstance(exc, ProviderNotFoundError):
        return _presentation(
            ErrorCategory.RESOURCE_NOT_FOUND,
            "RESOURCE NOT FOUND",
            "O recurso ou modelo solicitado não foi encontrado.",
            provider_name,
            http_status,
            "RESOURCE NOT FOUND",
            None,
            exc,
            raw_details,
        )
    source_name = type(root).__name__.lower()
    if (
        isinstance(root, (TimeoutError, asyncio.TimeoutError))
        or isinstance(exc, ProviderTimeoutError)
        or "timeout" in source_name
        or "timedout" in source_name
    ):
        return _presentation(
            ErrorCategory.REQUEST_TIMEOUT,
            "REQUEST TIMEOUT",
            "O provedor demorou além do tempo permitido para responder.",
            provider_name,
            http_status,
            "TIMEOUT",
            "Tente novamente mais tarde.",
            exc,
            raw_details,
        )
    if (
        isinstance(root, ConnectionError)
        or (
            isinstance(root, OSError)
            and root.errno
            in {
                errno.ECONNABORTED,
                errno.ECONNREFUSED,
                errno.ECONNRESET,
                errno.ENETDOWN,
                errno.ENETUNREACH,
                errno.EHOSTUNREACH,
            }
        )
        or isinstance(exc, ProviderConnectionError)
        or "connection" in source_name
        or "connecterror" in source_name
    ):
        return _presentation(
            ErrorCategory.CONNECTION_FAILURE,
            "CONNECTION FAILURE",
            "Não foi possível estabelecer conexão com o provedor.",
            provider_name,
            http_status,
            "CONNECTION ERROR",
            "Verifique a conexão e tente novamente.",
            exc,
            raw_details,
        )
    if http_status == 503 or isinstance(exc, ProviderUnavailableError):
        return _presentation(
            ErrorCategory.SERVICE_UNAVAILABLE,
            "SERVICE UNAVAILABLE",
            "O serviço está temporariamente indisponível.",
            provider_name,
            http_status,
            "SERVICE UNAVAILABLE",
            "Tente novamente mais tarde.",
            exc,
            raw_details,
        )
    if http_status is not None and http_status >= 500:
        return _presentation(
            ErrorCategory.PROVIDER_ERROR,
            "PROVIDER ERROR",
            "O provedor encontrou uma falha ao processar a solicitação.",
            provider_name,
            http_status,
            "PROVIDER ERROR",
            "Tente novamente mais tarde.",
            exc,
            raw_details,
        )
    if http_status == 400 or isinstance(exc, ProviderInvalidRequestError):
        return _presentation(
            ErrorCategory.INVALID_REQUEST,
            "INVALID REQUEST",
            "O provedor rejeitou os parâmetros da solicitação.",
            provider_name,
            http_status,
            "REQUEST REJECTED",
            None,
            exc,
            raw_details,
        )
    if isinstance(exc, ProviderResponseError) or _is_invalid_response(root):
        return _presentation(
            ErrorCategory.RESPONSE_ERROR,
            "INVALID RESPONSE",
            "O provedor retornou uma resposta que não pôde ser processada.",
            provider_name,
            http_status,
            "RESPONSE ERROR",
            None,
            exc,
            raw_details,
        )
    if isinstance(exc, LLMException) and "RESOURCE_EXHAUSTED" in text:
        return _presentation(
            ErrorCategory.RESOURCE_EXHAUSTED,
            "RESOURCE LIMIT",
            "O limite de utilização da API foi atingido.",
            provider_name,
            http_status,
            _quota_kind(text),
            _format_retry(retry_after)
            or "Consulte a disponibilidade da quota antes de tentar novamente.",
            exc,
            raw_details,
        )
    return _presentation(
        ErrorCategory.UNKNOWN,
        "SYSTEM ALERT",
        "Não foi possível concluir o processamento.",
        provider_name,
        http_status,
        "UNKNOWN SYSTEM ERROR",
        None,
        exc,
        raw_details,
    )


def report_error(
    exc: BaseException,
    *,
    provider: str | None = None,
    model: str | None = None,
    debug: bool = False,
) -> ErrorPresentation:
    """Classifica e registra detalhes sanitizados sem propagar exceções ao terminal."""
    presentation = classify_error(exc, provider=provider)
    logging.getLogger("ultron.cli.errors").error(
        "CLI request failed",
        extra={
            "provider": presentation.provider,
            "model": model,
            "http_status": presentation.http_status,
            "category": presentation.category.value,
            "sanitized_message": presentation.details,
            "request_id": presentation.request_id,
            "debug_mode": debug,
        },
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return presentation


def _presentation(
    category: ErrorCategory,
    title: str,
    message: str,
    provider: str,
    http_status: int | None,
    status: str,
    retry_message: str | None,
    exc: BaseException,
    details: str,
) -> ErrorPresentation:
    request_id = getattr(exc, "request_id", None)
    return ErrorPresentation(
        category=category,
        title=title,
        message=message,
        provider=provider,
        http_status=http_status,
        status=status,
        retry_message=retry_message,
        source=type(_root_cause(exc)).__name__,
        details=details,
        request_id=str(request_id) if request_id else None,
    )


def _root_cause(exc: BaseException) -> BaseException:
    seen: set[int] = set()
    current = exc
    while current.__cause__ and id(current.__cause__) not in seen:
        seen.add(id(current))
        current = current.__cause__
    return current


def _http_status(exc: BaseException) -> int | None:
    for name in ("http_status", "status_code", "code"):
        value = getattr(exc, name, None)
        if isinstance(value, int) and 100 <= value <= 599:
            return value
    return None


def _provider_name(provider: str | None) -> str:
    return {
        "gemini": "GOOGLE GEMINI",
        "mock": "MOCK PROVIDER",
    }.get((provider or "").lower(), (provider or "LLM PROVIDER").upper())


def _quota_kind(text: str) -> str:
    if "perday" in text or "per day" in text or "requests_per_day" in text:
        return "DAILY QUOTA EXCEEDED"
    if "perminute" in text or "per minute" in text or "requests_per_minute" in text:
        return "PER-MINUTE QUOTA EXCEEDED"
    return "QUOTA EXCEEDED"


def _retry_after_seconds(*exceptions: BaseException) -> float | None:
    for exc in exceptions:
        for name in ("retry_after_seconds", "retry_after", "retry_delay"):
            value = getattr(exc, name, None)
            if isinstance(value, (int, float)):
                return float(value)
            seconds = getattr(value, "total_seconds", None)
            if callable(seconds):
                return float(seconds())
            if isinstance(value, str):
                match = _RETRY_SECONDS.search(value)
                if match:
                    return _seconds_from_match(match)

        text = sanitize_error_text(str(exc))
        clock = _RETRY_CLOCK.search(text)
        if clock and any(clock.group(name) for name in ("h", "m", "s")):
            return (
                int(clock.group("h") or 0) * 3600
                + int(clock.group("m") or 0) * 60
                + float(clock.group("s") or 0)
            )
        match = _RETRY_SECONDS.search(text)
        if match:
            return _seconds_from_match(match)
        for name in ("details", "metadata", "response_json"):
            metadata = getattr(exc, name, None)
            if metadata is not None:
                details = sanitize_error_text(json.dumps(metadata, default=str))
                match = _RETRY_SECONDS.search(details)
                if match:
                    return _seconds_from_match(match)
    return None


def _seconds_from_match(match: re.Match[str]) -> float:
    value = float(match.group("value"))
    unit = match.group("unit").lower()
    if unit.startswith("ms"):
        return value / 1000
    if unit.startswith("m"):
        return value * 60
    if unit.startswith("h"):
        return value * 3600
    return value


def _format_retry(seconds: float | None) -> str | None:
    if seconds is None or seconds < 0:
        return None
    total = max(1, round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    if secs or not parts:
        parts.append(f"{secs} s")
    return "Aguarde aproximadamente " + " ".join(parts) + " antes de tentar novamente."


def _is_invalid_response(exc: BaseException) -> bool:
    return isinstance(
        exc,
        (AttributeError, TypeError, ValueError, json.JSONDecodeError),
    ) and not isinstance(
        exc, ProviderInvalidRequestError
    )


def logs_directory() -> Path:
    """Retorna o diretório convencional de logs da aplicação."""
    return Path("logs")
