"""Validação formal dos 8 critérios de aceitação do MVP do ULTRON.

Critérios Verificados:
1. Iniciar o ULTRON (FastAPI startup & health check).
2. Criar uma conversa.
3. Enviar uma mensagem.
4. Receber uma resposta do Google Gemini.
5. Continuar a conversa preservando o contexto.
6. Recuperar conversas anteriores e histórico.
7. Modificar instruções de personalidade.
8. Trocar a configuração de provedor sem alterar a lógica core da aplicação.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.dependencies import get_db_session
from app.config import get_settings
from app.database.models import Base
from app.intelligence.personality.personality_config import PersonalityConfig
from app.intelligence.prompt_engine import PromptEngine
from app.intelligence.providers.gemini import GeminiProvider
from app.intelligence.providers.mock import MockProvider
from app.intelligence.providers.registry import (
    ProviderRegistry,
    get_provider_registry,
)
from app.main import create_app


@pytest.fixture
async def mvp_client() -> AsyncGenerator[AsyncClient, None]:
    """Prepara cliente de teste assíncrono para o MVP."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    settings = get_settings()
    registry = ProviderRegistry(default_provider_id="mock")
    registry.register_provider(MockProvider(default_model="mock-v1"))

    # Registrar Gemini se a chave estiver presente
    gemini_key = settings.get_gemini_api_key()
    if gemini_key:
        registry.register_provider(
            GeminiProvider(api_key=gemini_key, default_model=settings.GEMINI_DEFAULT_MODEL)
        )

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_provider_registry] = lambda: registry

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_criterion_1_start_ultron(mvp_client: AsyncClient):
    """Critério 1: Iniciar o ULTRON com sucesso e verificar saúde."""
    resp = await mvp_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "ULTRON"


@pytest.mark.asyncio
async def test_criterion_2_and_3_create_conversation_and_send_message(
    mvp_client: AsyncClient,
):
    """Critérios 2 e 3: Criar uma conversa e enviar uma mensagem."""
    req = {
        "message": "Qual é a primeira diretriz do ULTRON?",
        "provider": "mock",
    }
    resp = await mvp_client.post("/api/v1/chat", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_id" in data
    assert data["role"] == "assistant"
    assert len(data["content"]) > 0


@pytest.mark.asyncio
async def test_criterion_4_receive_gemini_response_live(mvp_client: AsyncClient):
    """Critério 4: Receber resposta real do provedor Gemini."""
    settings = get_settings()
    if not settings.get_gemini_api_key():
        pytest.skip("Chave GEMINI_API_KEY não configurada no ambiente para teste live.")

    req = {
        "message": "Responda apenas a palavra: ATIVO",
        "provider": "gemini",
        "temperature": 0.1,
    }
    resp = await mvp_client.post("/api/v1/chat", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "gemini"
    assert "ATIVO" in data["content"].upper()
    assert data["usage"]["total_tokens"] > 0


@pytest.mark.asyncio
async def test_criterion_5_continue_conversation_with_context(mvp_client: AsyncClient):
    """Critério 5: Continuar a conversa preservando o contexto."""
    # 1. Primeira mensagem
    resp1 = await mvp_client.post(
        "/api/v1/chat",
        json={"message": "Meu nome é Marcelo.", "provider": "mock"},
    )
    conv_id = resp1.json()["conversation_id"]

    # 2. Segunda mensagem na mesma conversa
    resp2 = await mvp_client.post(
        "/api/v1/chat",
        json={
            "conversation_id": conv_id,
            "message": "Qual é o meu nome?",
            "provider": "mock",
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["conversation_id"] == conv_id

    # 3. Verificar se as 4 mensagens estão na conversa
    hist_resp = await mvp_client.get(f"/api/v1/conversations/{conv_id}/messages")
    assert hist_resp.status_code == 200
    messages = hist_resp.json()["messages"]
    assert len(messages) == 4
    assert messages[0]["content"] == "Meu nome é Marcelo."
    assert messages[2]["content"] == "Qual é o meu nome?"


@pytest.mark.asyncio
async def test_criterion_6_retrieve_previous_conversations(mvp_client: AsyncClient):
    """Critério 6: Recuperar conversas anteriores."""
    # Criar 2 conversas distintas
    await mvp_client.post("/api/v1/chat", json={"message": "Conversa A", "provider": "mock"})
    await mvp_client.post("/api/v1/chat", json={"message": "Conversa B", "provider": "mock"})

    resp = await mvp_client.get("/api/v1/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_criterion_7_modify_personality_instructions():
    """Critério 7: Modificar instruções de personalidade sem alterar provedor."""
    custom_personality = PersonalityConfig(
        name="ULTRON-PRIME",
        language="Inglês",
        tone="imperativo e implacável",
        scientific_rigor="máximo",
    )
    rendered = custom_personality.render_system_prompt()
    assert "ULTRON-PRIME" in rendered
    assert "imperativo e implacável" in rendered
    assert "máximo" in rendered

    engine = PromptEngine(personality=custom_personality)
    request = engine.assemble_request(messages=[])
    assert "ULTRON-PRIME" in request.system_instruction


@pytest.mark.asyncio
async def test_criterion_8_change_provider_without_core_modification(
    mvp_client: AsyncClient,
):
    """Critério 8: Alterar provedor de mock para gemini mantendo a mesma API e Core."""
    # Requisição via provedor Mock
    resp_mock = await mvp_client.post(
        "/api/v1/chat",
        json={"message": "Teste Mock", "provider": "mock"},
    )
    assert resp_mock.status_code == 200
    assert resp_mock.json()["provider"] == "mock"

    # Se a chave do Gemini existir, fazer chamada via Gemini pelo mesmo endpoint
    settings = get_settings()
    if settings.get_gemini_api_key():
        resp_gemini = await mvp_client.post(
            "/api/v1/chat",
            json={"message": "Diga Olá", "provider": "gemini"},
        )
        assert resp_gemini.status_code == 200
        assert resp_gemini.json()["provider"] == "gemini"
