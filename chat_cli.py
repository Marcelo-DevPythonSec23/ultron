"""CLI interativo para conversar diretamente com o ULTRON pelo terminal."""

import asyncio

from app.api.dependencies import (
    get_chat_service,
    get_context_manager,
    get_conversation_repository,
    get_message_repository,
    get_orchestrator,
    get_prompt_engine,
)
from app.config import get_settings
from app.database.connection import get_session_factory, init_db
from app.intelligence.providers.registry import get_provider_registry
from app.models.conversation import ChatRequest


async def start_cli() -> None:
    """Inicia o loop interativo de conversação no terminal."""
    await init_db()
    settings = get_settings()
    session_factory = get_session_factory()
    prompt_engine = get_prompt_engine()
    context_manager = get_context_manager(settings)
    registry = get_provider_registry()

    print("\n" + "=" * 50)
    print(f"  ULTRON ONLINE — Provedor Ativo: {settings.DEFAULT_LLM_PROVIDER}")
    print("  Digite sua mensagem ou 'sair' para encerrar.")
    print("=" * 50 + "\n")

    conversation_id: str | None = None

    while True:
        try:
            user_input = input("Você: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("sair", "exit", "quit"):
                print("\nULTRON: Encerrando conexão.\n")
                break

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
                response = await orchestrator.process_chat(request)
                conversation_id = response.conversation_id

                print(f"\nULTRON: {response.content}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nULTRON: Sessão interrompida.\n")
            break
        except Exception as exc:  # noqa: BLE001
            print(f"\n[Erro no processamento]: {exc}\n")


if __name__ == "__main__":
    asyncio.run(start_cli())
