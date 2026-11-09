"""Configuração de logs estruturados e sanitização de segredos do ULTRON."""

import json
import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, ClassVar


class SensitiveDataFilter(logging.Filter):
    """Filtro para mascarar chaves, senhas, tokens e credenciais em URLs."""

    PATTERNS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (re.compile(r"(GEMINI_API_KEY\s*=\s*)([^\s]+)", re.IGNORECASE), r"\1[MASCARADO]"),
        (re.compile(r"(AIza[0-9A-Za-z\-_]{30,40})"), "[MASCARADO]"),
        (re.compile(r"(AQ\.[0-9A-Za-z\-_]{40,})"), "[MASCARADO]"),
        (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_\.=]+", re.IGNORECASE), r"\1[MASCARADO]"),
        (re.compile(r"(?i)(https?://)[^\s/@:]+:[^\s/@]+@"), r"\1[MASCARADO]@"),
        (
            re.compile(
                r'("?(?:api[_-]?key|password|secret|token|authorization)"?'
                r'\s*[:=]\s*"?)([^"\\s,}]+)("?)',
                re.IGNORECASE,
            ),
            r"\1[MASCARADO]\3",
        ),
    ]
    _secrets: ClassVar[set[str]] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {key: self.mask_value(value) for key, value in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.mask_value(value) for value in record.args)
        return True

    @classmethod
    def mask_sensitive_text(cls, text: str) -> str:
        masked = text
        for pattern, replacement in cls.PATTERNS:
            masked = pattern.sub(replacement, masked)
        for secret in cls._secrets:
            if secret:
                masked = masked.replace(secret, "[MASCARADO]")
        return masked

    @classmethod
    def register_secrets(cls, secrets: list[str | None]) -> None:
        cls._secrets.update(secret for secret in secrets if secret)

    @classmethod
    def mask_value(cls, value: Any) -> Any:
        if isinstance(value, str):
            return cls.mask_sensitive_text(value)
        return value


class SanitizingFormatter(logging.Formatter):
    """Sanitiza todo o registro renderizado, inclusive stack traces."""

    def format(self, record: logging.LogRecord) -> str:
        return SensitiveDataFilter.mask_sensitive_text(super().format(record))


class JsonLogFormatter(SanitizingFormatter):
    """Serializa eventos de log com campos de diagnóstico estruturados."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
                "level": record.levelname,
                "logger": record.name,
                "message": super().format(record),
                "provider": getattr(record, "provider", None),
                "model": getattr(record, "model", None),
                "http_status": getattr(record, "http_status", None),
                "category": getattr(record, "category", None),
                "details": getattr(record, "sanitized_message", None),
                "request_id": getattr(record, "request_id", None),
            },
            ensure_ascii=False,
        )


def setup_logging(
    log_level: str = "INFO",
    *,
    console: bool = True,
    log_directory: str | Path = "logs",
    secrets: list[str | None] | None = None,
) -> logging.Logger:
    """Configura logs rotativos do app em arquivo e, opcionalmente, no console."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    SensitiveDataFilter.register_secrets(secrets or [])
    logger = logging.getLogger("ultron")
    logger.setLevel(level)

    for existing in list(logger.handlers):
        if getattr(existing, "_ultron_managed", False):
            logger.removeHandler(existing)
            existing.close()

    directory = Path(log_directory)
    directory.mkdir(parents=True, exist_ok=True)
    formatter = JsonLogFormatter()
    handlers: list[logging.Handler] = [
        RotatingFileHandler(
            directory / "ultron.log",
            maxBytes=5_000_000,
            backupCount=3,
            encoding="utf-8",
        ),
        RotatingFileHandler(
            directory / "errors.log",
            maxBytes=5_000_000,
            backupCount=3,
            encoding="utf-8",
        ),
    ]
    handlers[0].setLevel(level)
    handlers[1].setLevel(logging.ERROR)

    if console:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(
            SanitizingFormatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handlers.append(stream_handler)

    for handler in handlers:
        handler._ultron_managed = True
        if handler.formatter is None:
            handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    return logger
