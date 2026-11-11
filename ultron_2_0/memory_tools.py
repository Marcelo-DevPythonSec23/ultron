"""Memória de fatos do ULTRON 2.0 (Etapa 4) — explícita, sob autoridade do ULTRON.

Reusa o gerenciador REAL do Mark-LVI (`memory/memory_manager.py`: esquema de
categorias, atualização, busca lexical, formatação e recorte) — não reimplementa
nada. O que muda é ONDE ele grava: o `MEMORY_PATH` do módulo é apontado, dentro
deste processo, para o diretório PRÓPRIO do 2.0 (`data/memory.json`). O arquivo
`Mark-LVI-main/memory/long_term.json` nunca é lido nem escrito (regra §3.1).

Política de persistência (master prompt §9, Etapa 4 do plano):

* NADA é salvo automaticamente. Só uma chamada explícita a `remember` grava.
* Resultado de ferramenta NÃO vira memória; o histórico durável da conversa
  continua sendo o do núcleo do lain (SQLite).
* `recall` é leitura pura (não escreve).
* `forget` é destrutivo e exige confirmação: enquanto a interface de
  confirmação não estiver ligada, o gateway o recusa (comportamento seguro).
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from . import bootstrap
from .tool_contracts import ToolContract
from .tool_gateway import ToolGateway

logger = logging.getLogger("ultron2.memory")

# O `memory_manager` do Mark-LVI guarda o caminho em uma GLOBAL de módulo.
# Duas instâncias (dois escopos/arquivos) no mesmo processo corromperiam uma à
# outra se cada operação não reafirmasse o próprio caminho. Este lock serializa
# "apontar o caminho + executar a operação" (o manager tem lock próprio apenas
# para o I/O, não para a global).
_path_lock = threading.RLock()

MEMORY_CATEGORIES = (
    "identity",
    "preferences",
    "projects",
    "relationships",
    "wishes",
    "notes",
)

_memory_manager: Any = None
_active_path: Path | None = None


def default_memory_path() -> Path:
    """Arquivo de memória do 2.0 — nunca o long_term.json do Mark-LVI."""
    return bootstrap.ULTRON2_ROOT / "data" / "memory.json"


def _manager():
    global _memory_manager
    if _memory_manager is None:
        bootstrap.ensure_sys_paths()
        from memory import memory_manager  # módulo REAL do Mark-LVI

        _memory_manager = memory_manager
    return _memory_manager


def configure_memory_path(path: str | Path | None = None) -> Path:
    """Aponta o gerenciador reutilizado para o arquivo do 2.0 (idempotente)."""
    global _active_path
    target = Path(path).resolve() if path is not None else default_memory_path()
    manager = _manager()
    manager.MEMORY_PATH = target
    _active_path = target
    return target


class FactMemory:
    """Fachada explícita sobre o memory_manager reutilizado.

    Toda operação reafirma `self.path` sob `_path_lock` antes de tocar no
    manager: o caminho do memory_manager é uma global de módulo e, sem isso,
    uma segunda instância (outro escopo/teste) desviaria as gravações.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = configure_memory_path(path)
        self._manager = _manager()

    def _use(self):
        """Aponta o manager para ESTA instância; exige `_path_lock` do chamador."""
        self._manager.MEMORY_PATH = self.path
        return self._manager

    def remember(
        self,
        key: str,
        value: str,
        category: str = "notes",
        memory_type: str | None = None,
    ) -> dict[str, Any]:
        key = (key or "").strip()
        value = (value or "").strip()
        if not key:
            raise ValueError("key vazia")
        if not value:
            raise ValueError("value vazio")
        category = category if category in MEMORY_CATEGORIES else "notes"
        with _path_lock:
            self._use().remember(key, value, category)
        return {
            "stored": True,
            "category": category,
            "key": key,
            "value": value,
        }

    def recall(self, query: str = "", limit: int = 8) -> str:
        with _path_lock:
            return self._use().search_memory(query or "", limit=max(1, int(limit)))

    def forget(self, key: str, category: str = "notes") -> dict[str, Any]:
        category = category if category in MEMORY_CATEGORIES else "notes"
        with _path_lock:
            message = self._use().forget((key or "").strip(), category)
        removed = message.startswith("Forgotten:")
        return {"removed": removed, "category": category, "message": message}

    def entries(self) -> list[dict[str, Any]]:
        with _path_lock:
            return self._use().all_entries_for_ui()

    def forget_all(self) -> None:  # pragma: no cover - ferramenta de teste
        with _path_lock:
            manager = self._use()
            manager.save_memory(manager._empty_memory())


def register_memory_tools(
    gateway: ToolGateway, memory: Any | None = None
) -> Any:
    """Registra remember/recall/forget no gateway (allowlist do ULTRON).

    Aceita `FactMemory` (armazenamento bruto, compatível com a Etapa 4) ou um
    `MemoryEngine` (memória tipada/versionada). Os dois expõem o mesmo contrato
    mínimo `remember/recall/forget`, então o gateway não muda.
    """
    memory = memory or FactMemory()

    def remember_executor(parameters: dict) -> str:
        facts = memory.remember(
            parameters["key"],
            parameters["value"],
            parameters.get("category", "notes"),
            parameters.get("memory_type"),
        )
        return json.dumps(facts, ensure_ascii=False)

    def recall_executor(parameters: dict) -> str:
        return json.dumps(
            {
                "query": parameters.get("query", ""),
                "facts": memory.recall(
                    parameters.get("query", ""),
                    int(parameters.get("limit", 8)),
                ),
            },
            ensure_ascii=False,
        )

    def forget_executor(parameters: dict) -> str:
        facts = memory.forget(
            parameters["key"], parameters.get("category", "notes")
        )
        return json.dumps(facts, ensure_ascii=False)

    _category_schema = {
        "type": "STRING",
        "description": "Memory category.",
        "enum": list(MEMORY_CATEGORIES),
    }
    _memory_type_schema = {
        "type": "STRING",
        "description": (
            "Memory type. 'user' for the person's preferences/identity, "
            "'semantic' for stable facts, 'episodic' for a past event, "
            "'procedural' for a validated how-to. Default: semantic."
        ),
        "enum": ["semantic", "user", "episodic", "procedural"],
    }

    gateway.register(
        ToolContract(
            name="remember",
            description=(
                "Store ONE durable fact the user explicitly asked you to "
                "remember (a preference, a project, a person, a wish or a "
                "note). Never call this for ordinary conversation or for tool "
                "output. Creating memory is an explicit user request."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "key": {"type": "STRING", "description": "Short fact key."},
                    "value": {"type": "STRING", "description": "Fact content."},
                    "category": _category_schema,
                    "memory_type": _memory_type_schema,
                },
                "required": ["key", "value"],
            },
            required_fields=["key", "value"],
            timeout_seconds=5.0,
            requires_confirmation=False,
            permissions=["memory:write"],
            source="ultron-2.0/memory_tools.py (schema: Mark-LVI memory_manager)",
            expected_errors=["empty key", "empty value"],
        ),
        remember_executor,
    )

    gateway.register(
        ToolContract(
            name="recall",
            description=(
                "Search stored durable facts about the user. Use when the "
                "user asks what you remember, or when a stored preference is "
                "needed. Read-only: never writes memory."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Keywords; empty lists everything."},
                    "limit": {"type": "INTEGER", "description": "Max facts (default 8)."},
                },
                "required": [],
            },
            required_fields=[],
            timeout_seconds=5.0,
            requires_confirmation=False,
            permissions=["memory:read"],
            source="ultron-2.0/memory_tools.py (schema: Mark-LVI memory_manager)",
            expected_errors=["memory file unreadable"],
        ),
        recall_executor,
    )

    gateway.register(
        ToolContract(
            name="forget",
            description=(
                "Permanently delete ONE stored fact. Destructive: requires "
                "explicit user confirmation."
            ),
            parameters={
                "type": "OBJECT",
                "properties": {
                    "key": {"type": "STRING", "description": "Fact key to delete."},
                    "category": _category_schema,
                },
                "required": ["key"],
            },
            required_fields=["key"],
            timeout_seconds=5.0,
            requires_confirmation=True,
            permissions=["memory:write", "memory:delete"],
            source="ultron-2.0/memory_tools.py (schema: Mark-LVI memory_manager)",
            expected_errors=["fact not found"],
        ),
        forget_executor,
    )

    logger.info("Ferramentas de memória registradas (arquivo=%s)", memory.path)
    return memory
