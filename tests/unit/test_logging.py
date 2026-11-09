"""Testes unitários para o sistema de logging e mascaramento de segredos."""

from app.utils.logging import SensitiveDataFilter


def test_sensitive_data_filter_masks_api_key():
    """Valida que padrões de chaves de API conhecidas são mascarados."""
    sample_text = "Conectando com chave AIzaSyD9876543210AbCdEfGhIjKlMnOpQrStU no host"
    masked = SensitiveDataFilter.mask_sensitive_text(sample_text)
    assert "AIzaSyD9876543210AbCdEfGhIjKlMnOpQrStU" not in masked
    assert "[MASCARADO]" in masked


def test_sensitive_data_filter_masks_bearer_token():
    """Valida que tokens Bearer são mascarados."""
    sample_text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    masked = SensitiveDataFilter.mask_sensitive_text(sample_text)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz" not in masked
    assert "[MASCARADO]" in masked
