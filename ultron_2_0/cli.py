"""CLI de texto do ULTRON 2.0 — interface primária (master prompt §5.1).

Loop REPL que encaminha CADA linha ao orquestrador do lain via
OrchestratorBridge — o mesmo caminho que a voz usará na Etapa 3 (master
prompt §6.1: o resultado do STT segue o MESMO fluxo do texto; não existe um
segundo mecanismo de conversação para voz).

Comandos de interface (não vão ao modelo):
    /status   — estado real do núcleo (providers, ferramentas, conversa)
    /tools    — ferramentas integradas e seus contratos
    /new      — encerra a conversa atual; próximo turno abre outra
    /quit     — sai

Nada aqui decide por conta própria: sem fallback regex, sem eco (o antigo
`voice_runner.py`, que ecoava a mensagem do usuário e executava comandos
por regex — um segundo mecanismo de decisão — foi removido; ver
docs/INTEGRATION_MAP.md).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .orchestrator_bridge import OrchestratorBridge

logger = logging.getLogger("ultron2.cli")

_COMMANDS = ("/status", "/tools", "/new", "/quit")


def _print_response(response) -> None:
    """Imprime um ChatResponse do lain com metadados curtos."""
    print(f"\n{response.content}\n")
    meta = []
    if response.provider:
        meta.append(f"provider={response.provider}")
    if response.model:
        meta.append(f"model={response.model}")
    usage = getattr(response.usage, "total_tokens", 0)
    if usage:
        meta.append(f"tokens={usage}")
    if meta:
        print(f"  [{' | '.join(meta)}]\n")


def _print_status(bridge: OrchestratorBridge) -> None:
    status = bridge.status()
    if not status.get("ready"):
        print(f"\n  [núcleo não iniciado]\n  {status}\n")
        return
    print("\n  ULTRON 2.0 — estado real do sistema")
    print(f"  provedor padrão : {status['default_provider']}")
    print(f"  providers        : {', '.join(status['providers'])}")
    print(f"  ferramentas      : {', '.join(status['tools']) or '(nenhuma)'}")
    print(f"  banco            : {status['database']}")
    print(f"  conversa         : {status['conversation_id'] or '(nova no próximo turno)'}")
    print()


def _print_tools(bridge: OrchestratorBridge) -> None:
    gateway = bridge.runtime.gateway
    if gateway is None or not gateway.list_contracts():
        print("\n  (nenhuma ferramenta integrada)\n")
        return
    print()
    for contract in gateway.list_contracts():
        req = ", ".join(contract.required_fields) or "—"
        print(f"  {contract.name}({req})")
        print(f"    {contract.description}")
        print(f"    fonte: {contract.source} | timeout: {contract.timeout_seconds:.0f}s")
        if contract.expected_errors:
            print(f"    erros conhecidos: {', '.join(contract.expected_errors)}")
        print()
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ultron2",
        description="ULTRON 2.0 — núcleo ULTRON (lain) + ferramentas Mark-LVI",
    )
    parser.add_argument(
        "--provider", default=None,
        help="provedor do núcleo (mock, gemini...; padrão: auto)",
    )
    parser.add_argument(
        "--database", default=None,
        help="URL do banco do 2.0 (padrão: ultron-2.0/data/ultron2.db)",
    )
    parser.add_argument(
        "--no-tools", action="store_true",
        help="desliga o gateway de ferramentas (só conversa)",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="executa uma demonstração não-interativa e sai",
    )
    parser.add_argument(
        "--voice", action="store_true",
        help="inicia a interface de voz (STT Gemini Live + TTS) em vez do REPL",
    )
    parser.add_argument(
        "--message", default=None,
        help="envia uma única mensagem e sai (modo one-shot)",
    )
    parser.add_argument(
        "--project-root", default=None,
        help="raiz que contém lain/ e Mark-LVI-main/ (padrão: auto)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="logging em nível DEBUG",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.voice:
        # A voz é outra interface para o MESMO núcleo: delega ao runner e
        # repassa apenas opções de núcleo (sem duplicar a lógica de conversa).
        from .voice.runner import main as voice_main

        voice_argv: list[str] = []
        for flag, value in (
            ("--provider", args.provider),
            ("--database", args.database),
            ("--project-root", args.project_root),
        ):
            if value:
                voice_argv.extend([flag, value])
        if args.verbose:
            voice_argv.append("--verbose")
        return voice_main(voice_argv)

    bridge = OrchestratorBridge(
        project_root=args.project_root,
        database_url=args.database,
        default_provider=args.provider,
        enable_tools=not args.no_tools,
    )

    if args.demo:
        with bridge:
            _print_status(bridge)
            _print_tools(bridge)
        return 0

    if args.message:
        with bridge:
            _print_response(bridge.process_text(args.message))
        return 0

    with bridge:
        _print_status(bridge)
        print("  Comandos de interface: /status  /tools  /new  /quit\n")
        while True:
            try:
                line = input("ultron> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if not line:
                continue
            if line in ("/quit", "/exit", "/sair"):
                return 0
            if line == "/status":
                _print_status(bridge)
                continue
            if line == "/tools":
                _print_tools(bridge)
                continue
            if line == "/new":
                bridge.new_conversation()
                print("  [próximo turno abre uma conversa nova]\n")
                continue
            try:
                _print_response(bridge.process_text(line))
            except Exception as exc:  # falha controlada: interface continua de pé
                logger.exception("falha ao processar turno")
                print(f"\n  [erro] {type(exc).__name__}: {exc}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
