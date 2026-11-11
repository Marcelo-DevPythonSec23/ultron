"""Criptografia OPCIONAL em repouso para a memória (Fase 6).

Usa `cryptography.fernet` se estiver instalado; senão, desativa graciosamente
(segredo: não é uma dependência obrigatória, AGENTS.md §4.6).

A chave nunca é impressa, logada ou duplicada. Ela é esperada via variável de
ambiente `ULTRON2_MEMORY_ENCRYPTION_KEY` (32 bytes base64-urlsafe) ou gerada
uma única vez e armazenada em um arquivo separado (`memory.key`) ao lado do
banco — nunca dentro dos arquivos de dados criptografados.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("ultron2.memory.encryption")

_KEY_ENV = "ULTRON2_MEMORY_ENCRYPTION_KEY"


def available() -> bool:
    """Indica se a criptografia está disponível (dependência opcional)."""
    return _available() and _load_key() is not None


def _available() -> bool:
    try:
        __import__("cryptography")
        return True
    except ImportError:
        return False


def _load_key(key_file: str | Path | None = None) -> bytes | None:
    """Carrega a chave de criptografia sem expô-la em logs.

    Ordem: variável de ambiente `ULTRON2_MEMORY_ENCRYPTION_KEY` > arquivo
    `key_file` (padrão: `memory.key` ao lado do banco) > None (desabilitado).
    A chave pode estar em base64 (formato Fernet) ou raw (32 bytes).
    """
    env_key = os.environ.get(_KEY_ENV)
    if env_key:
        try:
            return base64.urlsafe_b64decode(env_key)
        except Exception:  # chave inválida no ambiente
            logger.warning("%s inválido; criptografia desabilitada", _KEY_ENV)
            return None
    if key_file is None:
        key_file = Path(__file__).resolve().parent / "memory.key"
    key_path = Path(key_file)
    if key_path.exists():
        try:
            raw = key_path.read_bytes().strip()
            # O arquivo pode guardar a chave em base64 (formato Fernet) ou raw.
            try:
                return base64.urlsafe_b64decode(raw)
            except Exception:
                return raw
        except OSError as exc:
            logger.warning("não foi possível ler %s: %s", key_path, exc)
            return None
    return None


class MemoryEncryption:
    """Criptografia opcional em repouso para arquivos de memória."""

    def __init__(self, key_file: str | Path | None = None) -> None:
        self.available = _available() and _load_key(key_file) is not None
        self._key = _load_key(key_file) if self.available else None
        self._fernet = None
        if self.available:
            try:
                from cryptography.fernet import Fernet

                self._fernet = Fernet(self._key)
            except Exception as exc:  # noqa: BLE001
                logger.warning("cryptography instalado mas não pôde ser usado: %s", exc)
                self.available = False

    def encrypt_bytes(self, data: bytes) -> bytes:
        if not self.available:
            raise RuntimeError("criptografia não disponível (cryptography ou chave ausente)")
        assert self._fernet is not None
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        if not self.available:
            raise RuntimeError("criptografia não disponível (cryptography ou chave ausente)")
        assert self._fernet is not None
        return self._fernet.decrypt(data)

    def public(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "package": "cryptography",
        }


def generate_key_file(key_file: str | Path = "memory.key") -> bool:
    """Gera um novo arquivo de chave (se ainda não existir). Devolve True se criou."""
    from cryptography.fernet import Fernet  # type: ignore

    path = Path(key_file)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(Fernet.generate_key())
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    logger.info("chave de criptografia gerada em %s", path)
    return True


__all__ = ["MemoryEncryption", "generate_key_file", "available"]
