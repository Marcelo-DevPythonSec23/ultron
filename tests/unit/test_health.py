"""Testes unitários para o endpoint de health check."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint():
    """Valida se a rota /api/v1/health retorna status 200 e campos esperados."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data
        assert "active_provider" in data
        assert "timestamp" in data
