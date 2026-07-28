import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import groq
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.config import Settings
from api.routes import health
from api.suggestor.groq import (
    GroqSuggestor,
    classify_provider_failure,
    model_availability,
)


def completion(content: str, model: str = "openai/gpt-oss-20b") -> SimpleNamespace:
    usage = SimpleNamespace(
        model_dump=lambda: {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
            "prompt_tokens_details": {"cached_tokens": 0},
        }
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        model=model,
        usage=usage,
    )


@pytest.fixture(autouse=True)
def reset_availability_registry():
    model_availability.reset()
    yield
    model_availability.reset()


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (groq.APITimeoutError(httpx.Request("GET", "https://example.com")), "timeout"),
        (
            groq.APIConnectionError(message="x", request=httpx.Request("GET", "https://example.com")),
            "connection_error",
        ),
        (ValueError("bad shape"), "invalid_contract"),
    ],
)
def test_classify_provider_failure_basic(exc, expected):
    assert classify_provider_failure(exc) == expected


def test_classify_model_not_found_from_provider_code():
    request = httpx.Request("GET", "https://api.groq.com/openai/v1/models/x")
    response = httpx.Response(404, request=request)
    exc = groq.NotFoundError(
        "missing",
        response=response,
        body={"error": {"code": "model_not_found"}},
    )
    assert classify_provider_failure(exc) == "model_not_found"


def test_classify_unsupported_parameter_from_provider_code():
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(400, request=request)
    exc = groq.BadRequestError(
        "bad",
        response=response,
        body={"error": {"code": "unsupported_parameter"}},
    )
    assert classify_provider_failure(exc) == "unsupported_parameter"


def test_canary_success_updates_availability_and_redacts_secrets(caplog, monkeypatch):
    client = MagicMock()
    client.models.retrieve.side_effect = lambda model: SimpleNamespace(id=model)
    client.chat.completions.create.return_value = completion(
        '{"candidates":["canaryprobe.com"]}'
    )
    settings = Settings(monitoring_canary_token="test-token")
    suggestor = GroqSuggestor(client=client, settings=settings)

    with caplog.at_level("INFO"):
        result = suggestor.run_gpt_oss_canary()

    assert result.status == "ok"
    assert result.models["default"]["status"] == "ok"
    assert result.models["creative"]["status"] == "ok"
    assert result.checks["default_contract"]["status"] == "ok"
    assert "canaryprobe.com" not in json.dumps(result.as_dict())
    assert "PROMPT" not in caplog.text
    assert settings.groq_api_key is None or settings.groq_api_key not in caplog.text
    assert model_availability.get(settings.groq_model).available is True
    assert model_availability.get(settings.groq_creative_model).available is True


def test_canary_reports_model_not_found_without_contract_call(caplog):
    request = httpx.Request("GET", "https://api.groq.com/openai/v1/models/x")
    response = httpx.Response(
        404,
        request=request,
        headers={"x-request-id": "req-canary-404"},
    )
    missing = groq.NotFoundError(
        "gone",
        response=response,
        body={"error": {"code": "model_not_found"}},
    )
    client = MagicMock()
    client.models.retrieve.side_effect = missing
    suggestor = GroqSuggestor(client=client)

    with caplog.at_level("WARNING"):
        result = suggestor.run_gpt_oss_canary()

    assert result.status == "error"
    assert result.models["default"]["error_class"] == "model_not_found"
    assert result.checks["default_contract"]["status"] == "skipped"
    assert client.chat.completions.create.call_count == 0
    event = next(
        json.loads(record.message)
        for record in caplog.records
        if '"event": "llm_canary_completed"' in record.message
    )
    assert event["status"] == "error"
    assert event["default_error_class"] == "model_not_found"


def test_health_canary_requires_token(monkeypatch):
    monkeypatch.setenv("MONITORING_CANARY_TOKEN", "secret-canary")
    # Clear cached settings if any
    from api import config

    config.get_settings.cache_clear() if hasattr(config.get_settings, "cache_clear") else None

    app = FastAPI()
    app.include_router(health.router)
    monkeypatch.setattr(
        health,
        "get_settings",
        lambda: Settings(monitoring_canary_token="secret-canary"),
    )
    # Mock the class so construction never touches the real Groq client
    # (which requires GROQ_API_KEY). The route does GroqSuggestor().run_gpt_oss_canary.
    mock_suggestor = MagicMock()
    mock_suggestor.run_gpt_oss_canary.return_value = SimpleNamespace(
        status="ok",
        as_dict=lambda: {"status": "ok", "latency_ms": 1, "models": {}, "checks": {}},
    )
    monkeypatch.setattr(health, "GroqSuggestor", MagicMock(return_value=mock_suggestor))

    client = TestClient(app)
    assert client.get("/health/canary").status_code == 401
    ok = client.get("/health/canary", headers={"X-Canary-Token": "secret-canary"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "ok"
    mock_suggestor.run_gpt_oss_canary.assert_called_once()


def test_health_check_exposes_reason_and_safe_db_error(monkeypatch):
    settings = Settings()
    model_availability.set(settings.groq_creative_model, False, "provider_permission_denied")
    monkeypatch.setattr(health, "get_settings", lambda: settings)
    monkeypatch.setattr(health, "_check_database_connection", AsyncMock())

    payload = json.loads(asyncio.run(health.health_check()).body)
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["groq_creative"] == "unavailable"
    assert payload["dependencies"]["groq_creative_reason"] == "provider_permission_denied"

    monkeypatch.setattr(
        health,
        "_check_database_connection",
        AsyncMock(side_effect=RuntimeError("postgres://user:password@db/secret")),
    )
    response = asyncio.run(health.health_check())
    body = json.loads(response.body)
    assert response.status_code == 503
    assert body["error"] == "RuntimeError"
    assert "password" not in response.body.decode()
