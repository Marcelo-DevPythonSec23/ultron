"""Servidor do HUD web do ULTRON 2.0.

Sobe o MESMO núcleo da CLI/voz e serve a interface em 127.0.0.1 por padrão.
A voz não é iniciada aqui: ela tem um processo próprio
(`python -m ultron_2_0.voice`) para não abrir microfone sem pedido explícito.

Uso:

    python -m ultron_2_0.web
    python -m ultron_2_0.web --port 8765 --provider mock --database sqlite+aiosqlite:///:memory:
"""

from __future__ import annotations

import argparse
import logging
import webbrowser

from ..orchestrator_bridge import OrchestratorBridge
from .app import create_app

logger = logging.getLogger("ultron2.web.server")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ultron2.web", description="ULTRON 2.0 — HUD web local"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--database", default=None)
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--no-tools", action="store_true")
    parser.add_argument("--open", action="store_true", help="abre o navegador")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    try:
        import uvicorn
    except ImportError:
        print(
            "uvicorn não está instalado. Rode:\n"
            "  uv pip install --python .venv/bin/python uvicorn"
        )
        return 2

    bridge = OrchestratorBridge(
        project_root=args.project_root,
        database_url=args.database,
        default_provider=args.provider,
        enable_tools=not args.no_tools,
    )
    bridge.start()
    app = create_app(bridge)
    url = f"http://{args.host}:{args.port}"
    print(f"ULTRON 2.0 — HUD em {url}")
    if args.open:
        webbrowser.open(url)
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
