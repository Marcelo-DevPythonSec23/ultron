"""Backup e restauração da memória (Fase 6).

Cria um arquivo ZIP contendo os três arquivos canônicos da memória do 2.0
(`memory.json`, `memory_records.json`, `memory_history.json`) com um
manifesto de metadados. Não expor credenciais: o manifesto não contém o
conteúdo dos fatos, apenas contagens e caminhos.

Operações não destrutivas: o backup só lê; a restauração sobrescreve os
arquivos de destino (explicitamente solicitado pelo operador).
"""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("ultron2.memory.backup")

MEMORY_FILES = ("memory.json", "memory_records.json", "memory_history.json")


@dataclass
class BackupManifest:
    created_at: str
    source_dir: str
    files: list[str]
    record_count: int
    history_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "source_dir": self.source_dir,
            "files": list(self.files),
            "record_count": self.record_count,
            "history_count": self.history_count,
        }


def _counts(dir_path: Path) -> tuple[int, int]:
    """Conta registros e entradas de histórico (para o manifesto, sem expor conteúdo)."""
    records = 0
    history = 0
    try:
        data = json.loads((dir_path / "memory_records.json").read_text(encoding="utf-8"))
        records = len(data.get("records", []))
    except Exception:
        pass
    try:
        data = json.loads((dir_path / "memory_history.json").read_text(encoding="utf-8"))
        history = len(data.get("entries", []))
    except Exception:
        pass
    return records, history


def backup_memory(
    source_dir: str | Path,
    dest_zip: str | Path,
) -> dict[str, Any]:
    """Faz backup dos arquivos de memória em um ZIP.

    Devolve um dicionário com `ok`, `zip_path`, `manifest` e, em caso de
    falha, `error`. Nunca escreve nos projetos originais (`lain/`,
    `Mark-LVI-main/`): `source_dir` deve ser um diretório do 2.0.
    """
    source = Path(source_dir).resolve()
    dest = Path(dest_zip).resolve()
    if not source.is_dir():
        return {"ok": False, "error": f"diretório de origem não encontrado: {source}"}

    missing = [f for f in MEMORY_FILES if not (source / f).exists()]
    if missing:
        return {
            "ok": False,
            "error": f"arquivos de memória ausentes em {source}: {missing}",
        }

    record_count, history_count = _counts(source)
    manifest = BackupManifest(
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source_dir=str(source),
        files=list(MEMORY_FILES),
        record_count=record_count,
        history_count=history_count,
    )

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest.as_dict(), indent=2, ensure_ascii=False))
            for fname in MEMORY_FILES:
                zf.write(source / fname, arcname=fname)
        logger.info(
            "backup de memória criado: %s (registros=%d, histórico=%d)",
            dest,
            record_count,
            history_count,
        )
        return {
            "ok": True,
            "zip_path": str(dest),
            "manifest": manifest.as_dict(),
        }
    except Exception as exc:  # noqa: BLE001 — falha de backup não derruba o núcleo
        logger.exception("falha ao criar backup de memória: %s", exc)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def restore_memory(
    source_zip: str | Path,
    dest_dir: str | Path,
    *,
    confirm: bool = False,
) -> dict[str, Any]:
    """Restaura arquivos de memória a partir de um ZIP.

    `confirm` deve ser True para realmente sobrescrever (evita restauração
    acidental). Só restaura os três arquivos canônicos; ignora o resto do ZIP.
    """
    if not confirm:
        return {
            "ok": False,
            "error": "restauração requer confirm=True (operação destrutiva explícita)",
        }

    src = Path(source_zip).resolve()
    dest = Path(dest_dir).resolve()
    if not src.is_file():
        return {"ok": False, "error": f"arquivo de backup não encontrado: {src}"}
    if not dest.is_dir():
        return {"ok": False, "error": f"diretório de destino não encontrado: {dest}"}

    restored: list[str] = []
    try:
        with zipfile.ZipFile(src, "r") as zf:
            names = set(zf.namelist())
            for fname in MEMORY_FILES:
                if fname in names:
                    data = zf.read(fname)
                    (dest / fname).write_bytes(data)
                    restored.append(fname)
        logger.info("memória restaurada de %s para %s (%d arquivos)", src, dest, len(restored))
        return {
            "ok": True,
            "restored": restored,
            "zip_path": str(src),
            "dest_dir": str(dest),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("falha ao restaurar memória: %s", exc)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


__all__ = ["BackupManifest", "backup_memory", "restore_memory", "MEMORY_FILES"]
