"""`python -m ultron_2_0` — ponto de entrada do pacote ULTRON 2.0.

Equivalente a executar `main.py` a partir do diretório ultron-2.0/.
"""

from __future__ import annotations

import runpy
from pathlib import Path

_here = Path(__file__).resolve().parent
_main_py = _here.parent / "main.py"

if __name__ == "__main__":
    raise SystemExit(runpy.run_path(str(_main_py), run_name="__main__"))
