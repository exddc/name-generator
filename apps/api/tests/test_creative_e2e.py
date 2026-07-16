import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from api.config import Settings
from api.models.api_models import RequestDomainSuggestion
from api.routes import domain as domain_routes
from api.security import AuthenticatedUser
from api.suggestor.groq import GroqSuggestor


def test_creative_button_request_uses_120b_end_to_end(monkeypatch):
    """Exercise the API path used when the frontend sends creative=true."""
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"candidates":["creativeproof.com"]}'
                )
            )
        ],
        model="openai/gpt-oss-120b",
        usage=SimpleNamespace(
            model_dump=lambda: {
                "prompt_tokens": 20,
                "completion_tokens": 5,
                "total_tokens": 25,
            }
        ),
    )
    client = MagicMock()
    client.chat.completions.create.return_value = completion
    settings = Settings(groq_creative_fallback_to_default=False)
    suggestor = GroqSuggestor(client=client, settings=settings)
    monkeypatch.setattr(domain_routes, "GroqSuggestor", lambda: suggestor)

    suggestion_record = SimpleNamespace(
        id=266,
        model="openai/gpt-oss-120b",
        save=AsyncMock(),
    )
    create_suggestion = AsyncMock(return_value=suggestion_record)
    monkeypatch.setattr(domain_routes.SuggestionDB, "create", create_suggestion)
    monkeypatch.setattr(
        domain_routes,
        "enqueue_and_wait",
        AsyncMock(
            return_value=[
                {"domain": "creativeproof.com", "status": "available"}
            ]
        ),
    )
    monkeypatch.setattr(domain_routes, "upsert_domain_in_db", AsyncMock())
    monkeypatch.setattr(domain_routes.MetricsTracker, "save", AsyncMock())

    async def exercise_creative_request() -> str:
        response = await domain_routes.suggest_stream(
            RequestDomainSuggestion(
                description="A playful writing tool",
                count=1,
                creative=True,
            ),
            AuthenticatedUser(user_id="e2e-user"),
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        await asyncio.sleep(0)
        return "".join(chunks)

    body = asyncio.run(exercise_creative_request())

    provider_request = client.chat.completions.create.call_args.kwargs
    assert provider_request["model"] == "openai/gpt-oss-120b"
    assert provider_request["include_reasoning"] is False
    assert provider_request["stream"] is False
    assert provider_request["response_format"]["json_schema"]["strict"] is True
    assert create_suggestion.call_args.kwargs["model"] == "openai/gpt-oss-120b"
    assert '"requested_model": "openai/gpt-oss-120b"' in body
    assert '"model": "openai/gpt-oss-120b"' in body
    assert '"fallback_used": false' in body
