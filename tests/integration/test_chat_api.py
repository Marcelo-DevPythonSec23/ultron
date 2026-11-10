"""Testes de integração para as rotas /api/v1/chat e histórico de conversas."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.dependencies import get_db_session
from app.database.models import Base
from app.intelligence.providers.mock import MockProvider
from app.intelligence.providers.registry import (
    ProviderRegistry,
    get_provider_registry,
)
from app.main import create_app


@pytest.fixture
async def app_with_test_db() -> AsyncGenerator[AsyncClient, None]:
    """Cria uma instância do app com banco em memória e MockProvider para testes de API."""
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

    mock_registry = ProviderRegistry(default_provider_id="mock")
    mock_registry.register_provider(MockProvider(fixed_response="Resposta de teste mockada"))

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_provider_registry] = lambda: mock_registry

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_chat_api_create_and_continue_conversation(app_with_test_db: AsyncClient):
    """Valida envio de mensagem, criação de conversa e continuidade do histórico."""
    client = app_with_test_db

    # 1. Enviar primeira mensagem (sem conversation_id)
    payload_1 = {
        "message": "Primeira pergunta do usuário",
        "provider": "mock",
    }
    resp_1 = await client.post("/api/v1/chat", json=payload_1)
    assert resp_1.status_code == 200
    data_1 = resp_1.json()
    assert "conversation_id" in data_1
    assert data_1["content"] == "Resposta de teste mockada"
    conv_id = data_1["conversation_id"]

    # 2. Enviar segunda mensagem na mesma conversa
    payload_2 = {
        "conversation_id": conv_id,
        "message": "Segunda pergunta do usuário",
        "provider": "mock",
    }
    resp_2 = await client.post("/api/v1/chat", json=payload_2)
    assert resp_2.status_code == 200
    data_2 = resp_2.json()
    assert data_2["conversation_id"] == conv_id

    # 3. Listar conversas
    resp_list = await client.get("/api/v1/conversations")
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == conv_id
    assert list_data["items"][0]["message_count"] == 4  # 2 do usuário + 2 do assistente

    # 4. Recuperar histórico de mensagens da conversa
    resp_hist = await client.get(f"/api/v1/conversations/{conv_id}/messages")
    assert resp_hist.status_code == 200
    hist_data = resp_hist.json()
    assert hist_data["conversation_id"] == conv_id
    assert len(hist_data["messages"]) == 4
    assert hist_data["messages"][0]["role"] == "user"
    assert hist_data["messages"][1]["role"] == "assistant"
    assert hist_data["messages"][2]["role"] == "user"
    assert hist_data["messages"][3]["role"] == "assistant"


@pytest.mark.asyncio
async def test_frontend_is_served_from_same_origin(app_with_test_db: AsyncClient):
    """Valida que a UI local é servida pelo backend que recebe as mensagens."""
    response = await app_with_test_db.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ULTRON" in response.text
    assert "DEFAULT_EP='/api/v1/chat'" in response.text
    assert "conversation_id:chat.serverId||null" in response.text


@pytest.mark.asyncio
async def test_chat_api_validation_error(app_with_test_db: AsyncClient):
    """Valida rejeição de mensagens vazias com 422."""
    client = app_with_test_db
    resp = await client.post("/api/v1/chat", json={"message": ""})
    assert resp.status_code == 422
