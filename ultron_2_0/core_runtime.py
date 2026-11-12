"""Runtime do núcleo ULTRON no ULTRON 2.0 — wiring real, sem eco.

Monta o núcleo ORIGINAL do lain por composição (master prompt §3.1: os
repositórios originais não são modificados; o trabalho ocorre aqui):

    Settings (CWD-independente, .env do lain por caminho absoluto)
    engine + session_factory (banco ISOLADO do 2.0 — nunca lain/ultron.db)
    ConversationRepository / MessageRepository
    ChatService -> ContextManager -> PromptEngine
    ProviderRegistry (mock + gemini, cada um envolvido pelo ToolCallingProvider)
    ModelRouter   <- Fase 3: seleção/fallback sobre o registry (autoridade)
    Orchestrator  <- o MESMO orquestrador do lain, único ciclo de conversa

A hierarquia de autoridade do master prompt §5.1 fica:

    interface (CLI texto / futura voz)
        -> Orchestrator do lain (contexto, memória, prompt, persistência)
            -> ModelRouter (Fase 3: seleção + fallback; NÃO é orquestrador)
                -> ProviderRegistry do lain (autoridade de registro)
                -> ToolCallingProvider (extensão 2.0: protocolo de ferramentas)
                    -> ToolGateway (contrato, validação, timeout)
                        -> actions do Mark-LVI (worker threads)

Gerenciamento de event loop: o runtime pode rodar de duas formas —

  * `start_background()` + `chat_sync()`/`run_coro()`: loop dedicado em thread
    de background (mesmo padrão do Mark-LVI para sessões de voz); chamadas
    síncronas usam `asyncio.run_coroutine_threadsafe`.
  * `start_async()` + `await chat(...))/await shutdown()`: dentro de um loop
    já ativo (pytest-asyncio, FastAPI futuro).

O banco é aberto em uma única AsyncSession de vida longa — os repositórios
do lain compartilham a sessão e cada operação deles faz commit. Chats
concorrentes são serializados pelo GIL + lock de sessão do aiosqlite.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from pathlib import Path

from . import bootstrap

logger = logging.getLogger("ultron2.core")


class UltronCoreRuntime:
    """Núcleo ULTRON montado e gerenciado pelo ULTRON 2.0."""

    def __init__(
        self,
        project_root: str | Path | None = None,
        database_url: str | None = None,
        default_provider: str | None = None,
        enable_tools: bool = True,
        memory_path: str | Path | None = None,
        memory_budget_chars: int = 1200,
        authorization: "AuthorizationManager | None" = None,
        confirmation_handler: "ConfirmationHandler | None" = None,
        router_config: "RouterConfig | None" = None,
    ) -> None:
        bootstrap.ensure_sys_paths(project_root)
        self._project_root, self._lain_root, self._marklvi_root = bootstrap.resolve_roots(
            project_root
        )

        self._database_url = database_url  # None -> banco isolado padrão do 2.0
        self._requested_default_provider = default_provider
        self._enable_tools = enable_tools
        # Memória é do NÚCLEO (MEMORY.md §2/§10), não uma ferramenta: o motor
        # existe mesmo com as ferramentas desligadas. `memory_path` permite
        # isolar arquivos em testes; em produção usa data/memory.json.
        self._memory_path = memory_path
        self._memory_budget_chars = max(0, int(memory_budget_chars))
        # Autorização (Fase 2): o modelo propõe, a interface decide. O manager
        # pode vir pronto (HUD/testes) ou ser criado com o handler interativo.
        self._authorization = authorization
        self._confirmation_handler = confirmation_handler
        # Fase 3: configuração do Model Router (env ULTRON_ROUTER_* por padrão).
        self._router_config = router_config

        # Event loop dedicado em thread de background (padrão Mark-LVI).
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None

        # Componentes do núcleo (populados em start()).
        self.settings = None
        self.orchestrator = None
        self.registry = None
        self.router = None  # ModelRouter (Fase 3)
        self.gateway = None
        self.authorization = None  # AuthorizationManager (Fase 2)
        self.memory = None  # FactMemory (armazenamento canônico, compat. Etapa 4)
        self.memory_engine = None  # MemoryEngine (tipos/escopos/versões)
        self._engine = None
        self._session_factory = None
        self._session = None
        self.agent_orchestrator = None  # AgentOrchestrator (Fase 4)
        self.integration_orchestrator = None  # IntegrationOrchestrator (Fase 5)

    @property
    def project_root(self) -> Path:
        """Raiz do projeto (contém lain/ e Mark-LVI-main/)."""
        return self._project_root

    # -- ciclo de vida --------------------------------------------------------
    async def start(self) -> "UltronCoreRuntime":
        """Inicializa settings, banco, gateway, providers e orquestrador.

        Idempotente: se o orquestrador já existe, apenas retorna self.
        """
        if self.orchestrator is not None:
            return self

        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )
        from sqlalchemy.pool import StaticPool

        from app.core.chat_service import ChatService
        from app.core.context_manager import ContextManager
        from app.core.orchestrator import Orchestrator
        from app.database.models import Base
        from app.database.repositories.conversation_repository import (
            ConversationRepository,
        )
        from app.database.repositories.message_repository import MessageRepository
        from app.intelligence.prompt_engine import PromptEngine
        from app.intelligence.providers.mock import MockProvider
        from app.intelligence.providers.registry import ProviderRegistry

        self.settings = bootstrap.build_settings(
            self._lain_root, database_url=self._database_url
        )
        db_url = self.settings.DATABASE_URL
        logger.info("Banco do ULTRON 2.0: %s", _mask_db_url(db_url))

        connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
        # :memory: exige StaticPool: sem ele, cada conexão do pool é um banco
        # vazio DIFERENTE (as tabelas criadas na conexão A somem na consulta
        # pela conexão B). O mesmo padrão está em lain/tests/conftest.py,
        # que roda cada teste num único engine em memória.
        pool_kwargs = (
            {"poolclass": StaticPool} if ":memory:" in db_url or db_url == "sqlite://" else {}
        )
        self._engine = create_async_engine(
            db_url, echo=False, future=True, connect_args=connect_args, **pool_kwargs
        )
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self._session_factory = async_sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )
        self._session = self._session_factory()

        # Memória do núcleo (MEMORY.md §2/§10): o motor existe SEMPRE — com as
        # ferramentas desligadas ele ainda fornece contexto ao modelo. O
        # armazenamento canônico continua sendo o memory.json do 2.0.
        from .memory_engine import MemoryEngine

        self.memory_engine = MemoryEngine(self._memory_path)
        self.memory = self.memory_engine.facts

        # Gateway de ferramentas (subset curado do Mark-LVI) — antes dos
        # providers, porque o ToolCallingProvider precisa dele.
        if self._enable_tools:
            from .authorization import AuthorizationManager
            from .marklvi_actions import build_gateway
            from .memory_tools import register_memory_tools

            self.gateway = build_gateway(self._project_root)
            # Toda ferramenta sensível passa por aqui; sem manager, o gateway
            # recusa. O handler interativo é da CLI; o HUD decide por endpoint.
            self.authorization = self._authorization or AuthorizationManager(
                confirm_handler=self._confirmation_handler
            )
            self.gateway.set_authorization(self.authorization)
            # remember/recall/forget passam a operar pelo motor: tipo, escopo,
            # versão e histórico. Memória explícita, sem gravação automática.
            register_memory_tools(self.gateway, self.memory_engine)
        else:
            self.gateway = None
            self.authorization = None

        default_provider = self._requested_default_provider or (
            "nvidia" if self._has_nvidia_api_key() else "gemini"
        )
        self.registry = ProviderRegistry(default_provider_id=default_provider)

        # Providers do núcleo, envolvidos pelo ToolCallingProvider quando há
        # ferramentas e pelo MemoryInjectionProvider (contexto do turno).
        # provider_id é o mesmo do interno: o orquestrador do lain não percebe
        # a extensão.
        #
        # O provedor MOCK está disponível APENAS para testes/depuração explícita
        # (via UltronCoreRuntime.register_provider com um MockProvider).
        # Ele NÃO é registrado automaticamente e NUNCA é o provedor padrão.
        if self.settings.get_gemini_api_key():
            from app.intelligence.providers.gemini import GeminiProvider

            gemini = GeminiProvider(
                api_key=self.settings.get_gemini_api_key(),
                default_model=self.settings.GEMINI_DEFAULT_MODEL,
            )
            self.registry.register_provider(self._wrap(gemini))
        else:
            logger.warning(
                "GEMINI_API_KEY ausente no .env do lain — provedor gemini não registrado"
            )

        # Provedor NVIDIA NIM como padrão (se configurado).
        # A chave vem exclusivamente de NVIDIA_API_KEY (variável de ambiente),
        # nunca é gravada em código nem exposta em logs.
        nvidia_api_key = self._get_nvidia_api_key()
        if nvidia_api_key:
            from .routing.providers.nvidia_nim import NVIDIAProvider

            nvidia = NVIDIAProvider(
                api_key=nvidia_api_key,
                default_model=os.environ.get("NVIDIA_DEFAULT_MODEL", "nvidia/nemotron-3.5-flash"),
            )
            self.registry.register_provider(self._wrap(nvidia))
            logger.info(
                "Provedor NVIDIA NIM registrado como padrão (modelo=%s)",
                nvidia.default_model,
            )
        else:
            logger.warning(
                "NVIDIA_API_KEY ausente — provedor NVIDIA NIM não registrado. "
                "Defina NVIDIA_API_KEY para usar o provedor NVIDIA NIM."
            )

        # Wiring final: o MESMO padrão de lain/app/api/dependencies.py
        # (repositórios -> ChatService -> ContextManager/PromptEngine -> Orchestrator).
        #
        # Fase 3: o Orchestrator recebe o ModelRouter (duck typing do registry).
        # O ProviderRegistry continua sendo a autoridade de REGISTRO; o router
        # apenas seleciona/encaminha e aplica timeout/retry/fallback.
        from .routing import ModelRouter

        self.router = ModelRouter(self.registry, config=self._router_config)

        chat_service = ChatService(
            conversation_repo=ConversationRepository(self._session),
            message_repo=MessageRepository(self._session),
        )
        self.orchestrator = Orchestrator(
            chat_service=chat_service,
            context_manager=ContextManager(
                max_tokens=self.settings.MAX_CONTEXT_TOKENS,
                max_messages=self.settings.MAX_HISTORY_MESSAGES,
            ),
            prompt_engine=PromptEngine(),
            provider_registry=self.router,
        )
        logger.info(
            "Núcleo ULTRON 2.0 pronto (provider padrão=%s, roteador=%s, ferramentas=%s)",
            default_provider,
            "ligado" if self.router.config.enabled else "desligado",
            ", ".join(self.gateway.names()) if self.gateway else "(desligadas)",
        )

        # Fase 4: Sistema Multiagente — orquestrador de agentes especializados.
        # Não é um segundo orquestrador conversacional: coordena agentes sob
        # solicitação do ULTRON, sem tocar no histórico, memória canônica nem
        # no process_text. Agentes iniciais usam ferramentas existentes (não
        # criam modelos próprios para o que já existe).
        from .agents import (
            AgentOrchestrator,
            ArchitectureAgent,
            DatabaseAgent,
            DeveloperAgent,
            QAAgent,
            ResearchAgent,
            SecurityAgent,
        )

        self.agent_orchestrator = AgentOrchestrator(max_concurrent=3)
        self.agent_orchestrator.register_agent(DeveloperAgent())
        self.agent_orchestrator.register_agent(ResearchAgent())
        self.agent_orchestrator.register_agent(SecurityAgent(gateway=self.gateway))
        self.agent_orchestrator.register_agent(QAAgent())
        self.agent_orchestrator.register_agent(DatabaseAgent())
        self.agent_orchestrator.register_agent(ArchitectureAgent())
        logger.info(
            "Multiagente pronto (tipos=%s)",
            ", ".join(self.agent_orchestrator.list_agent_types()),
        )

        # Fase 5: Integracao com agentes CLI e MCP.
        # Adaptadores independentes sobre interfaces reais do OpenCode
        # (`opencode run`, `opencode mcp list`). Processos isolados com timeout;
        # cada integracao pode ser habilitada/desabilitada individualmente.
        # Nao e um segundo orquestrador conversacional: apenas encaminha
        # tarefas especializadas a agentes/servidores externos.
        from .integrations import (
            IntegrationOrchestrator,
            MCPAdapter,
            OpenCodeAdapter,
        )

        self.integration_orchestrator = IntegrationOrchestrator()
        self.integration_orchestrator.register_integration(OpenCodeAdapter())
        self.integration_orchestrator.register_integration(MCPAdapter())
        logger.info(
            "Integracoes externas prontas (alvos=%s)",
            ", ".join(self.integration_orchestrator.list_integrations()["integrations"].keys()),
        )
        return self

    def _wrap(self, provider):
        """Envolve o provedor: ferramentas por dentro, memória por fora.

        Ordem importa: o `ToolCallingProvider` acrescenta o protocolo de
        ferramentas ao `system_instruction`; a memória entra como camada
        externa, uma vez por turno, e sobrevive às rodadas internas de
        ferramenta. Nenhum dos dois é um segundo orquestrador — ambos só
        transformam a requisição antes de o provedor interno respondê-la.
        """
        from .tool_loop import ToolCallingProvider

        wrapped = (
            ToolCallingProvider(provider, self.gateway)
            if self.gateway is not None
            else provider
        )
        if self.memory_engine is not None:
            from .memory_injection import MemoryInjectionProvider

            wrapped = MemoryInjectionProvider(
                wrapped,
                self.memory_engine,
                budget_chars=self._memory_budget_chars,
            )
        return wrapped

    def register_provider(self, provider) -> None:
        """Registra um provedor adicional no ProviderRegistry do lain.

        Recebe o MESMO tratamento dos provedores nativos: ferramentas
        (ToolCallingProvider) e memória (MemoryInjectionProvider), com o mesmo
        provider_id — registrar sob um id já existente o substitui,
        comportamento do ProviderRegistry do lain. Usado por testes e por
        integrações que tragam provedores próprios sem tocar no lain.
        """
        if self.orchestrator is None:
            raise RuntimeError(
                "núcleo não iniciado — chame start()/start_async() primeiro"
            )
        wrapped = self._wrap(provider)
        if self.router is not None:
            # O router delega o registro ao registry e atualiza o catálogo,
            # preservando a autoridade do ProviderRegistry do lain.
            self.router.register_provider(wrapped)
        else:
            self.registry.register_provider(wrapped)

    async def chat(
        self,
        message: str,
        conversation_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        system_instruction_override: str | None = None,
    ):
        """Uma rodada completa de conversa pelo orquestrador do lain."""
        from app.models.conversation import ChatRequest

        request = ChatRequest(
            conversation_id=conversation_id,
            message=message,
            provider=provider,
            model=model,
            temperature=temperature,
            system_instruction_override=system_instruction_override,
        )
        return await self.orchestrator.process_chat(request)

    def _get_nvidia_api_key(self) -> str | None:
        """Retorna a chave NVIDIA_API_KEY do ambiente (sem expor em logs)."""
        return os.environ.get("NVIDIA_API_KEY")

    def _has_nvidia_api_key(self) -> bool:
        """Indica se a chave NVIDIA_API_KEY está configurada."""
        return bool(self._get_nvidia_api_key())

    async def shutdown(self) -> None:
        """Encerra sessão e engine de forma ordenada."""
        if self._session is not None:
            try:
                await self._session.close()
            except Exception:  # pragma: no cover
                pass
            self._session = None
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
        self.orchestrator = None
        self.router = None
        self.agent_orchestrator = None
        self.integration_orchestrator = None
        logger.info("Núcleo ULTRON 2.0 encerrado.")

    # -- ponte síncrona -------------------------------------------------------
    def start_background(self) -> "UltronCoreRuntime":
        """Sobe o loop dedicado em thread e inicializa o núcleo nele."""
        if self._loop is not None and self._loop.is_running():
            return self
        if self.orchestrator is not None:
            return self
        loop = asyncio.new_event_loop()
        started = threading.Event()
        # started.set é agendado NO loop: só dispara depois que run_forever
        # está de fato processando callbacks — elimina a corrida entre
        # thread.start() e loop.is_running().
        loop.call_soon(started.set)
        self._loop = loop
        self._loop_thread = threading.Thread(
            target=self._run_loop_forever, args=(loop,), name="ultron2-core-loop", daemon=True
        )
        self._loop_thread.start()
        if not started.wait(timeout=10):  # pragma: no cover
            raise RuntimeError("loop dedicado do ULTRON 2.0 não subiu")
        return self.run_coro(self.start())

    @staticmethod
    def _run_loop_forever(loop: asyncio.AbstractEventLoop) -> None:
        """Roda o loop dedicado até stop_background() (corpo da thread)."""
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def start_async(self) -> "UltronCoreRuntime":
        """start() dentro de um loop já ativo (pytest-asyncio, FastAPI)."""
        return await self.start()

    def run_coro(self, coro):
        """Executa coroutine no loop dedicado (bloqueante para o chamador).

        Requer start_background(); em contexto já assíncrono, prefira
        start_async()/chat()/shutdown() com await direto.
        """
        if self._loop is None or not self._loop.is_running():
            raise RuntimeError(
                "loop dedicado não está ativo — chame start_background() "
                "ou use await start_async() num loop assíncrono"
            )
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def chat_sync(self, message: str, **kwargs):
        """chat() síncrono via run_coroutine_threadsafe no loop dedicado."""
        if self._loop is None or not self._loop.is_running():
            raise RuntimeError("runtime não iniciado — chame start_background()")
        future = asyncio.run_coroutine_threadsafe(self.chat(message, **kwargs), self._loop)
        return future.result()

    def stop_background(self) -> None:
        """Encerra o loop dedicado e o núcleo."""
        if self._loop is not None and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.shutdown(), self._loop).result()
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=5)
        self._loop = None
        self._loop_thread = None


def _mask_db_url(url: str) -> str:
    """Esconde caminhos completos em logs (limpeza de logging do master prompt)."""
    if url.startswith("sqlite"):
        tail = url.rsplit("/", 1)[-1] or "memory"
        return f"sqlite://…/{tail}"
    return "<non-sqlite>"
