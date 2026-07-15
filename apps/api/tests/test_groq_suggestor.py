import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from api.suggestor.groq import GroqSuggestor, _classify_api_error


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
    client.models.retrieve.return_value = SimpleNamespace(id="openai/gpt-oss-20b")
    return client


def test_request_uses_strict_schema_and_only_consumed_response_shape():
    client = fake_client(completion('{"candidates":["First.com","second.io","first.com"]}'))
    suggestor = GroqSuggestor(client=client)

    candidates = asyncio.run(suggestor.generate("a writing app", count=2))

    assert candidates == ["first.com", "second.io"]
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
        asyncio.run(suggestor.generate("DO-NOT-LOG-THIS-PROMPT", count=1))

    events = [json.loads(record.message) for record in caplog.records]
    completed = next(event for event in events if event["event"] == "llm_request_completed")
    assert completed["effective_model"] == "openai/gpt-oss-20b"
    assert "DO-NOT-LOG-THIS-PROMPT" not in caplog.text
    assert not suggestor.api_key or suggestor.api_key not in caplog.text


def test_startup_validation_checks_the_exact_model():
    client = fake_client(completion('{"candidates":["ready.com"]}'))
    suggestor = GroqSuggestor(client=client)

    suggestor.validate_model_availability()

    client.models.retrieve.assert_called_once_with("openai/gpt-oss-20b")


def test_provider_error_classification_supports_alert_labels():
    assert _classify_api_error(404, "model does not exist") == "model_not_found"
    assert _classify_api_error(400, "reasoning_effort is unsupported") == "unsupported_parameter"
    assert _classify_api_error(503, "service unavailable") == "provider_5xx"
