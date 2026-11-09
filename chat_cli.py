"""CLI interativo para conversar diretamente com o ULTRON pelo terminal."""

import argparse
import asyncio
from importlib.metadata import PackageNotFoundError, version

from app.api.dependencies import (
    get_chat_service,
    get_context_manager,
    get_conversation_repository,
    get_message_repository,
    get_orchestrator,
    get_prompt_engine,
)
from app.cli.error_handling import report_error
from app.cli.terminal import TerminalRenderer
from app.config import get_settings
from app.database.connection import get_session_factory, init_db
from app.intelligence.providers.registry import get_provider_registry
from app.models.conversation import ChatRequest
from app.utils.logging import setup_logging


def _application_version() -> str:
    try:
        return version("ultron")
    except PackageNotFoundError:
        return "development"


async def start_cli(debug: bool = False) -> None:
    """Inicia o loop interativo de conversação no terminal."""
    renderer = TerminalRenderer()
    renderer.begin_initialization()

    settings = get_settings()
    debug = debug or settings.DEBUG
    setup_logging(
        settings.LOG_LEVEL,
        console=False,
        secrets=[settings.get_gemini_api_key()],
    )

    with renderer.initialization_status("DATABASE"):
        await init_db()
    renderer.initialization_step("DATABASE", "READY")

    renderer.initialization_step("CONFIGURATION", "LOADED")

    session_factory = get_session_factory()
    prompt_engine = get_prompt_engine()
    context_manager = get_context_manager(settings)
    renderer.initialization_step("CONVERSATION CORE", "READY")

    registry = get_provider_registry()
    provider = registry.get_provider(settings.DEFAULT_LLM_PROVIDER)
    renderer.initialization_step("LLM PROVIDER", "CONFIGURED")
    renderer.show_header(
        version=_application_version(),
        provider=provider.provider_id,
        model=provider.default_model,
    )

    conversation_id: str | None = None

    while True:
        try:
            user_input = renderer.prompt()
            if not user_input:
                continue
            if user_input.lower() in ("sair", "exit", "quit"):
                renderer.show_shutdown("Connection terminated.")
                break

            renderer.show_user_message(user_input)
            async with session_factory() as session:
                conv_repo = get_conversation_repository(session)
                msg_repo = get_message_repository(session)
                chat_service = get_chat_service(conv_repo, msg_repo)
                orchestrator = get_orchestrator(
                    chat_service, context_manager, prompt_engine, registry
                )

                request = ChatRequest(
                    conversation_id=conversation_id,
                    message=user_input,
                )
                with renderer.response_stream() as on_chunk:
                    response = await orchestrator.process_chat(
                        request,
                        on_chunk=on_chunk,
                    )

                conversation_id = response.conversation_id
                renderer.show_assistant_message(response.content)

        except (KeyboardInterrupt, EOFError):
            renderer.show_shutdown("Session interrupted.")
            break
        except Exception as exc:  # noqa: BLE001
            error = report_error(
                exc,
                provider=provider.provider_id,
                model=provider.default_model,
                debug=debug,
            )
            renderer.show_error(error, debug=debug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ULTRON terminal interface")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show sanitized technical diagnostics for CLI errors.",
    )
    arguments = parser.parse_args()
    renderer = TerminalRenderer()
    try:
        asyncio.run(start_cli(debug=arguments.debug))
    except KeyboardInterrupt:
        renderer.show_shutdown("Session interrupted.")
    except Exception as exc:  # noqa: BLE001
        error = report_error(exc, debug=arguments.debug)
        renderer.show_error(error, debug=arguments.debug)
