"""Busca semântica OPCIONAL sobre a memória (Fase 6).

Este módulo NÃO torna embeddings uma dependência obrigatória
(AGENTS.md §4.6). Ele tenta importar um provedor de embeddings; se não
encontrar, desativa graciosamente e a memória cai de volta para a busca
léxica já existente em `MemoryEngine.search` (recuperação lexical preservada).

A interface é intencionalmente simples: indexar registros e consultar por
similaridade, sem alterar o armazenamento canônico nem o `MemoryEngine` base.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger("ultron2.memory.semantic")

# Nome do pacote opcional. Não é adicionado a requirements.txt: só usado se
# já estiver instalado no ambiente.
_EMBEDDINGS_PACKAGE = "sentence-transformers"


def available() -> bool:
    """Indica se o índice semântico está disponível (dependência opcional)."""
    return _available()


def _available() -> bool:
    try:
        __import__(_EMBEDDINGS_PACKAGE)
        return True
    except ImportError:
        return False


class SemanticIndex:
    """Índice semântico opcional.

    Se `sentence-transformers` não estiver instalado, `available` é False e
    todas as operações retornam resultados vazios sem levantar exceção — a
    memória continua funcionando com a busca léxica do `MemoryEngine`.
    """

    def __init__(self) -> None:
        self.available = _available()
        self._model = None
        self._embeddings: list[list[float]] = []
        self._records: list[dict[str, Any]] = []
        if self.available:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as exc:  # noqa: BLE001 — dependência opcional
                logger.warning(
                    "sentence-transformers instalado mas não pôde ser carregado: %s",
                    exc,
                )
                self.available = False

    # -- índice --------------------------------------------------------------
    def index_records(self, records: list[dict[str, Any]]) -> None:
        """Indexa registros para busca semântica (somente texto chave+valor)."""
        self._records = list(records or [])
        if not self.available or not self._records:
            self._embeddings = []
            return
        texts = [
            f"{r.get('key', '')} {r.get('value', '')}" for r in self._records
        ]
        try:
            embeddings = self._model.encode(texts, normalize_embeddings=True)
            self._embeddings = [list(map(float, e)) for e in embeddings]
        except Exception as exc:  # noqa: BLE001
            logger.warning("falha ao gerar embeddings: %s", exc)
            self.available = False
            self._embeddings = []

    # -- consulta ------------------------------------------------------------
    def query(self, text: str, top_k: int = 8) -> list[dict[str, Any]]:
        """Devolve os `top_k` registros mais similares (índice por posição)."""
        if not self.available or not self._embeddings or not text:
            return []
        try:
            q_emb = self._model.encode([text], normalize_embeddings=True)[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("falha ao consultar embeddings: %s", exc)
            self.available = False
            return []

        scores = [
            (self._cosine(q_emb, emb), idx)
            for idx, emb in enumerate(self._embeddings)
        ]
        scores.sort(key=lambda item: item[0], reverse=True)
        top_k = max(1, int(top_k))
        return [self._records[idx] for _, idx in scores[:top_k] if _ > 0]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def public(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "package": _EMBEDDINGS_PACKAGE,
            "indexed_records": len(self._records),
        }


__all__ = ["SemanticIndex", "available"]
