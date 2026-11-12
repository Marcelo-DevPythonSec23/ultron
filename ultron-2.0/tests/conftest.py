"""Fixtures compartilhadas dos testes do ULTRON 2.0.

Importar `ultron_2_0` resolve lain/ e Mark-LVI-main/ no sys.path (ver
ultron_2_0/__init__.py), de modo que os fakes e os testes podem importar
`app.*` (núcleo lain) diretamente — os MESMOS objetos que o runtime usa.
"""

from __future__ import annotations

import ultron_2_0  # noqa: F401 — resolve lain/ e Mark-LVI-main/ no sys.path

# Banco em memória por teste — nunca lain/ultron.db nem o banco do 2.0.
MEMORY_DB = "sqlite+aiosqlite:///:memory:"
