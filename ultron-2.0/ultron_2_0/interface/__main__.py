"""Ponto de entrada da interface desktop ULTRON 2.0.

Uso:
    python -m ultron_2_0.interface
"""

from __future__ import annotations

import sys

from .application import Application


def main() -> int:
    app = Application()
    if not app.initialize():
        print("falha ao inicializar a interface desktop", file=sys.stderr)
        return 1
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
