"""Configuração de logging estruturado e mascaramento de segredos para o ULTRON."""

import logging
import re
import sys
from typing import Any, ClassVar


class SensitiveDataFilter(logging.Filter):
    """Filtro de logging para sanitizar chaves de API, senhas e tokens sensíveis."""

    PATTERNS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (re.compile(r"(GEMINI_API_KEY\s*=\s*)([^\s]+)", re.IGNORECASE), r"\1[MASCARADO]"),
        (re.compile(r"(AIza[0-9A-Za-z\-_]{30,40})"), "[MASCARADO]"),
        (re.compile(r"(AQ\.[0-9A-Za-z\-_]{40,})"), "[MASCARADO]"),
        (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_\.=]+", re.IGNORECASE), r"\1[MASCARADO]"),
        (
            re.compile(r'("?(?:api[_-]?key|password|secret|token)"?\s*[:=]\s*"?)([^"\\s,]+)("?)', re.IGNORECASE),
            r"\1[MASCARADO]\3",
        ),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.mask_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.mask_value(v) for v in record.args)
        return True

    @classmethod
    def mask_sensitive_text(cls, text: str) -> str:
        masked = text
        for pattern, replacement in cls.PATTERNS:
            masked = pattern.sub(replacement, masked)
        return masked

    @classmethod
    def mask_value(cls, val: Any) -> Any:
        if isinstance(val, str):
            return cls.mask_sensitive_text(val)
        return val


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configura o logger raiz com formatação uniforme e filtro de segurança."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Obter logger raiz da aplicação
    logger = logging.getLogger("ultron")
    logger.setLevel(level)

    # Remover handlers duplicados se existirem
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    return logger
