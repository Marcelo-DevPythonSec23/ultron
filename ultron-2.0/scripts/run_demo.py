#!/usr/bin/env python
"""Demonstração não-interativa do ULTRON 2.0 (boot real + contratos).

Uso (a partir de ultron-2.0/):
    ./.venv/bin/python scripts/run_demo.py

Sobe o núcleo com banco em MEMÓRIA (não toca nenhum banco real), imprime o
estado real do sistema e os contratos das ferramentas integradas, roda um
turno de conversa com o provedor mock e encerra de forma ordenada.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ultron_2_0.cli import main


if __name__ == "__main__":
    raise SystemExit(
        main(
            [
                "--demo",
                "--database", "sqlite+aiosqlite:///:memory:",
                "--provider", "mock",
            ]
        )
    )
