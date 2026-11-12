#!/usr/bin/env python3
"""`main.py` — ponto de entrada único do software ULTRON 2.0.

Uso:
    python main.py                    # menu interativo de escolha da interface
    python main.py --cli              # CLI de texto (REPL)
    python main.py --web              # HUD web (FastAPI/uvicorn, 127.0.0.1:8765)
    python main.py --desktop          # interface desktop PySide6 (janela)
    python main.py --demo             # estado + ferramentas e sai

A interface desktop está conectada ao mesmo OrchestratorBridge usado pela
CLI e pelo HUD web — não há segundo cérebro, nem histórico paralelo.
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn


def _run_cli() -> int:
    """Interface de texto (REPL/one-shot/demo)."""
    from ultron_2_0.cli import main

    return main()


def _run_web() -> int:
    """HUD web local."""
    import uvicorn

    from ultron_2_0.web.server import build_app

    app = build_app()
    print("HUD web ULTRON 2.0 — http://127.0.0.1:8765")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
    return 0


def _run_desktop() -> int:
    """Interface desktop PySide6 conectada ao backend ULTRON."""
    from ultron_2_0.interface.application import Application

    app = Application()
    if not app.initialize():
        print("falha ao inicializar a interface desktop", file=sys.stderr)
        return 1
    return app.run()


def _run_demo() -> int:
    """Exibe estado e ferramentas disponíveis e sai."""
    from ultron_2_0.cli import main

    # Força modo demo via argv temporário
    old_argv = sys.argv
    sys.argv = ["ultron_2_0", "--demo"]
    try:
        return main()
    finally:
        sys.argv = old_argv


def _interactive_menu() -> int:
    """Menu interativo de escolha da interface."""
    print("╔═════════════════════════════════════════════════════════════╗")
    print("║              ULTRON 2.0 — interface desktop / web / CLI      ║")
    print("╠═════════════════════════════════════════════════════════════╣")
    print("║  1) CLI de texto          (REPL, /status, /tools, /new)      ║")
    print("║  2) HUD web               (http://127.0.0.1:8765)            ║")
    print("║  3) Interface desktop     (PySide6, janela com avatar)       ║")
    print("║  4) Demo                  (estado + ferramentas e sai)       ║")
    print("║  0) Sair                                                     ║")
    print("╚═════════════════════════════════════════════════════════════╝")
    print()

    escolha = input("Escolha a interface [1-4, 0]: ").strip()

    if escolha == "1":
        return _run_cli()
    if escolha == "2":
        return _run_web()
    if escolha == "3":
        return _run_desktop()
    if escolha == "4":
        return _run_demo()
    if escolha == "0":
        print("Até logo!")
        return 0

    print("Opção inválida.", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="ULTRON 2.0 — ponto de entrada único do software completo.",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="interface de texto (CLI REPL)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="HUD web local (FastAPI/uvicorn)",
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="interface desktop PySide6 (janela com avatar)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="exibe estado e ferramentas e sai",
    )
    args = parser.parse_args()

    if args.cli:
        return _run_cli()
    if args.web:
        return _run_web()
    if args.desktop:
        return _run_desktop()
    if args.demo:
        return _run_demo()

    # Sem argumento: menu interativo
    return _interactive_menu()


if __name__ == "__main__":
    raise SystemExit(main())
