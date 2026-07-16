import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import groq
import httpx
import pytest

from api.config import Settings
from api.exceptions import GenerationFailedError, ServiceUnavailableError
from api.suggestor.groq import GenerationResult, GroqSuggestor, model_availability
from api.suggestor.prompts import PromptType


def completion(content: str, model: str = "openai/gpt-oss-20b") -> SimpleNamespace:
    usage = SimpleNamespace(
        model_dump=lambda: {
            "prompt_tokens": 100,
            "completion_tokens": 25,
            "total_tokens": 125,
        }
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        model=model,
        usage=usage,
    )


def fake_client(response: SimpleNamespace) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value = response
    client.models.retrieve.side_effect = lambda model: SimpleNamespace(id=model)
    return client


@pytest.fixture(autouse=True)
def reset_availability_registry():
    model_availability.reset()
    yield
    model_availability.reset()


def test_request_uses_strict_schema_and_only_consumed_response_shape():
    client = fake_client(completion('{"candidates":["First.com","second.io","first.com"]}'))
    suggestor = GroqSuggestor(client=client)

    result = asyncio.run(suggestor.generate("a writing app", count=2))

    assert result.candidates == ["first.com", "second.io"]
    assert result.model == "openai/gpt-oss-20b"
    assert result.usage["total_tokens"] == 125
    assert result.cost_usd == 0.000015
    parameters = client.chat.completions.create.call_args.kwargs
    assert parameters["model"] == "openai/gpt-oss-20b"
    assert parameters["reasoning_effort"] == "low"
    assert parameters["include_reasoning"] is False
    assert parameters["stream"] is False
    assert parameters["response_format"]["type"] == "json_schema"
    assert parameters["response_format"]["json_schema"]["strict"] is True


def test_effective_model_is_logged_without_prompt_or_key(caplog):
    client = fake_client(completion('{"candidates":["quietlog.com"]}'))
    suggestor = GroqSuggestor(client=client)

    with caplog.at_level("INFO"):
        suggestor.validate_model_availability()

    assert '"effective_model": "openai/gpt-oss-20b"' in caplog.text
    assert '"effective_model": "openai/gpt-oss-120b"' in caplog.text
    assert not suggestor.api_key or suggestor.api_key not in caplog.text


def test_startup_validation_checks_the_exact_model():
    client = fake_client(completion('{"candidates":["ready.com"]}'))
    suggestor = GroqSuggestor(client=client)

    suggestor.validate_model_availability()

    assert client.models.retrieve.call_args_list == [
        (("openai/gpt-oss-20b",),),
        (("openai/gpt-oss-120b",),),
    ]


@pytest.mark.parametrize(
    ("prompt_type", "expected_model"),
    [
        (PromptType.LEGACY, "openai/gpt-oss-20b"),
        (PromptType.PERSONALIZED, "openai/gpt-oss-20b"),
        (PromptType.SIMILAR, "openai/gpt-oss-20b"),
        (PromptType.LEXICON, "openai/gpt-oss-120b"),
    ],
)
def test_selector_routes_only_lexicon_to_120b(prompt_type, expected_model):
    from api.suggestor.groq import select_model_profile

    assert select_model_profile(prompt_type, Settings()).model == expected_model


def test_concurrent_requests_do_not_leak_model_selection():
    client = MagicMock()

    def response_for_request(**parameters):
        return completion('{"candidates":["isolated.com"]}', model=parameters["model"])

    client.chat.completions.create.side_effect = response_for_request
    suggestor = GroqSuggestor(client=client)

    async def generate_concurrently():
        return await asyncio.gather(
            suggestor.generate("default", prompt_type=PromptType.LEGACY),
            suggestor.generate("creative", prompt_type=PromptType.LEXICON),
            suggestor.generate("similar", prompt_type=PromptType.SIMILAR, similar_context=SimpleNamespace(source_domain="source.com")),
        )

    results = asyncio.run(generate_concurrently())

    assert [result.model for result in results] == [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    ]
    assert suggestor.model == "openai/gpt-oss-20b"


def test_creative_fallback_is_disabled_by_default(monkeypatch):
    suggestor = GroqSuggestor(client=MagicMock(), settings=Settings())

    async def unavailable(*args, **kwargs):
        raise ServiceUnavailableError("unavailable")

    monkeypatch.setattr(suggestor, "_generate_with_profile", unavailable)

    with pytest.raises(ServiceUnavailableError):
        asyncio.run(suggestor.generate("creative", prompt_type=PromptType.LEXICON))


def test_creative_fallback_is_explicit_and_records_actual_model(monkeypatch):
    settings = Settings(groq_creative_fallback_to_default=True)
    suggestor = GroqSuggestor(client=MagicMock(), settings=settings)
    profiles_seen = []

    async def generate_with_selected_profile(profile, *args, **kwargs):
        profiles_seen.append(profile.model)
        if profile.name == "creative":
            raise ServiceUnavailableError("unavailable")
        return GenerationResult(
            candidates=["fallback.com"],
            requested_model=profile.model,
            model=profile.model,
            profile_name=profile.name,
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            cost_usd=0.00000225,
            latency_ms=1,
        )

    monkeypatch.setattr(
        suggestor, "_generate_with_profile", generate_with_selected_profile
    )

    result = asyncio.run(
        suggestor.generate("creative", prompt_type=PromptType.LEXICON)
    )

    assert profiles_seen == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    assert result.requested_model == "openai/gpt-oss-120b"
    assert result.model == "openai/gpt-oss-20b"
    assert result.fallback_used


@pytest.mark.parametrize("creative_failure", ["timeout", "permission"])
def test_creative_startup_failure_is_scoped_to_creative_generation(
    creative_failure, monkeypatch
):
    client = fake_client(completion('{"candidates":["defaultstillworks.com"]}'))
    request = httpx.Request("GET", "https://api.groq.com/openai/v1/models/model")
    if creative_failure == "timeout":
        failure = groq.APITimeoutError(request)
    else:
        response = httpx.Response(
            403,
            request=request,
            headers={"x-request-id": "req-permission-test"},
        )
        failure = groq.PermissionDeniedError(
            "permission denied",
            response=response,
            body={"error": {"code": "model_not_permitted"}},
        )

    client.models.retrieve.side_effect = [
        SimpleNamespace(id="openai/gpt-oss-20b"),
        failure,
    ]
    suggestor = GroqSuggestor(client=client)

    statuses = suggestor.validate_model_availability()
    default_result = asyncio.run(
        suggestor.generate("ordinary", prompt_type=PromptType.LEGACY)
    )

    assert statuses["openai/gpt-oss-20b"].available is True
    assert statuses["openai/gpt-oss-120b"].available is False
    assert default_result.model == "openai/gpt-oss-20b"

    from api.routes import health

    monkeypatch.setattr(health, "_check_database_connection", AsyncMock())
    health_response = asyncio.run(health.health_check())
    health_payload = json.loads(health_response.body)
    assert health_response.status_code == 200
    assert health_payload["status"] == "degraded"
    assert health_payload["dependencies"]["groq_default"] == "ok"
    assert health_payload["dependencies"]["groq_creative"] == "unavailable"

    with pytest.raises(ServiceUnavailableError) as exc_info:
        asyncio.run(suggestor.generate("creative", prompt_type=PromptType.LEXICON))
    assert exc_info.value.status_code == 503
    assert "Creative generation" in exc_info.value.details


def test_creative_model_recovers_after_revalidation_ttl_without_restart(monkeypatch):
    settings = Settings(groq_creative_revalidation_seconds=0)
    client = fake_client(
        completion(
            '{"candidates":["creativeisback.com"]}',
            model="openai/gpt-oss-120b",
        )
    )
    request = httpx.Request("GET", "https://api.groq.com/openai/v1/models/model")
    client.models.retrieve.side_effect = [
        SimpleNamespace(id="openai/gpt-oss-20b"),
        groq.APITimeoutError(request),
        SimpleNamespace(id="openai/gpt-oss-120b"),
    ]
    suggestor = GroqSuggestor(client=client, settings=settings)
    statuses = suggestor.validate_model_availability()

    from api.routes import health

    monkeypatch.setattr(health, "_check_database_connection", AsyncMock())
    degraded = json.loads(asyncio.run(health.health_check()).body)
    assert statuses["openai/gpt-oss-120b"].available is False
    assert degraded["status"] == "degraded"
    assert degraded["dependencies"]["groq_creative"] == "unavailable"

    result = asyncio.run(
        suggestor.generate("creative recovered", prompt_type=PromptType.LEXICON)
    )
    recovered = json.loads(asyncio.run(health.health_check()).body)

    assert result.model == "openai/gpt-oss-120b"
    assert result.candidates == ["creativeisback.com"]
    assert recovered["status"] == "ok"
    assert recovered["dependencies"]["groq_creative"] == "ok"
    assert client.models.retrieve.call_args_list == [
        (("openai/gpt-oss-20b",),),
        (("openai/gpt-oss-120b",),),
        (("openai/gpt-oss-120b",),),
    ]


def test_provider_diagnostics_are_useful_and_redacted(caplog):
    prompt_secret = "PROMPT-SHOULD-NOT-BE-LOGGED"
    api_secret = "KEY-SHOULD-NOT-BE-LOGGED"
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(
        400,
        request=request,
        headers={"x-request-id": "req-safe-123"},
    )
    provider_error = groq.BadRequestError(
        f"invalid request containing {prompt_secret} and {api_secret}",
        response=response,
        body={
            "error": {
                "code": "json_schema_invalid",
                "message": prompt_secret,
            }
        },
    )
    client = MagicMock()
    client.chat.completions.create.side_effect = provider_error
    suggestor = GroqSuggestor(client=client)

    with caplog.at_level("WARNING"), pytest.raises(GenerationFailedError):
        asyncio.run(suggestor.generate("private prompt", prompt_type=PromptType.LEGACY))

    event = next(
        json.loads(record.message)
        for record in caplog.records
        if '"event": "llm_request_failed"' in record.message
    )
    assert event["provider_http_status"] == 400
    assert event["provider_error_code"] == "json_schema_invalid"
    assert event["provider_request_id"] == "req-safe-123"
    assert event["exception_type"] == "BadRequestError"
    assert prompt_secret not in caplog.text
    assert api_secret not in caplog.text


def test_unexpected_error_is_not_retried_and_logs_redacted_traceback(caplog):
    secret = "PRIVATE-PROMPT-IN-EXCEPTION"
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError(secret)
    suggestor = GroqSuggestor(client=client)

    with caplog.at_level("WARNING"), pytest.raises(GenerationFailedError):
        asyncio.run(suggestor.generate("private prompt", prompt_type=PromptType.LEGACY))

    assert client.chat.completions.create.call_count == 1
    event = next(
        json.loads(record.message)
        for record in caplog.records
        if '"error_class": "unexpected"' in record.message
    )
    assert event["exception_type"] == "RuntimeError"
    assert event["traceback"]
    assert secret not in caplog.text
