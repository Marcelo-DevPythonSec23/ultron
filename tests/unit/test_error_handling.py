"""Testes de classificação e apresentação segura de erros da CLI."""

import json

import pytest
from rich.console import Console

from app.cli.error_handling import ErrorCategory, classify_error
from app.cli.terminal import TerminalRenderer
from app.intelligence.providers.base import (
    LLMException,
    ProviderAccessDeniedError,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.utils.logging import setup_logging


@pytest.mark.parametrize(
    ("exception", "category", "status"),
    [
        (ProviderRateLimitError("limited", "gemini", http_status=429), ErrorCategory.RESOURCE_EXHAUSTED, 429),
        (ProviderAuthenticationError("rejected", "gemini", http_status=401), ErrorCategory.AUTHENTICATION_FAILED, 401),
        (ProviderAccessDeniedError("denied", "gemini", http_status=403), ErrorCategory.ACCESS_DENIED, 403),
        (ProviderNotFoundError("missing", "gemini", http_status=404), ErrorCategory.RESOURCE_NOT_FOUND, 404),
        (LLMException("provider fault", "gemini", http_status=500), ErrorCategory.PROVIDER_ERROR, 500),
        (ProviderUnavailableError("offline", "gemini", http_status=503), ErrorCategory.SERVICE_UNAVAILABLE, 503),
        (ProviderTimeoutError("timeout", "gemini"), ErrorCategory.REQUEST_TIMEOUT, None),
        (ProviderConnectionError("connection", "gemini"), ErrorCategory.CONNECTION_FAILURE, None),
        (ProviderResponseError("invalid", "gemini"), ErrorCategory.RESPONSE_ERROR, None),
        (RuntimeError("unclassified"), ErrorCategory.UNKNOWN, None),
    ],
)
def test_classifies_known_errors(exception, category, status):
    presentation = classify_error(exception)

    assert presentation.category == category
    assert presentation.http_status == status


def test_quota_classification_includes_limit_type_and_wait():
    exception = ProviderRateLimitError(
        "quota",
        "gemini",
        details="requests_per_day exceeded; retryDelay: 90s",
        http_status=429,
        retry_after_seconds=90,
    )

    presentation = classify_error(exception)

    assert presentation.status == "DAILY QUOTA EXCEEDED"
    assert "1 min 30 s" in presentation.retry_message
    assert "liberada" not in presentation.retry_message


def test_classification_handles_missing_optional_metadata():
    presentation = classify_error(ProviderUnavailableError("offline", "gemini"))

    assert presentation.http_status is None
    assert presentation.request_id is None
    assert presentation.retry_message


def test_normal_terminal_output_hides_json_and_credentials():
    output = Console(record=True, width=80, force_terminal=False)
    renderer = TerminalRenderer(output)
    presentation = classify_error(
        ProviderRateLimitError(
            "quota",
            "gemini",
            details='{"api_key":"private-value","error":{"code":429}}',
            http_status=429,
        )
    )

    renderer.show_error(presentation)
    visible = output.export_text()

    assert "private-value" not in visible
    assert '"api_key"' not in visible
    assert "RESOURCE EXHAUSTED" in visible
    assert "HTTP 429" in visible


def test_debug_terminal_output_is_sanitized():
    output = Console(record=True, width=100, force_terminal=False)
    renderer = TerminalRenderer(output)
    presentation = classify_error(
        ProviderRateLimitError(
            "quota",
            "gemini",
            details='{"api_key":"private-value"}',
            http_status=429,
        )
    )

    renderer.show_error(presentation, debug=True)
    visible = output.export_text()

    assert "SOURCE" in visible
    assert "logs/errors.log" in visible
    assert "private-value" not in visible
    assert "[MASCARADO]" in visible


def test_file_logs_are_structured_and_mask_configured_secrets(tmp_path):
    secret = "local-secret-that-is-not-a-known-key-format"
    logger = setup_logging(
        "INFO",
        console=False,
        log_directory=tmp_path,
        secrets=[secret],
    )
    try:
        try:
            raise RuntimeError(f"request failed with {secret}")
        except RuntimeError:
            logger.exception(
                "provider failure",
                extra={
                    "provider": "gemini",
                    "model": "test-model",
                    "http_status": 429,
                    "category": "RESOURCE EXHAUSTED",
                    "request_id": "request-123",
                },
            )
        for handler in logger.handlers:
            handler.flush()

        all_logs = (tmp_path / "ultron.log").read_text()
        errors = (tmp_path / "errors.log").read_text()
        record = json.loads(errors)
        assert secret not in all_logs + errors
        assert "[MASCARADO]" in errors
        assert record["provider"] == "gemini"
        assert record["http_status"] == 429
        assert record["request_id"] == "request-123"
        assert len((tmp_path / "ultron.log").read_text().splitlines()) == 1
    finally:
        setup_logging("INFO", console=False, log_directory=tmp_path / "reset")
