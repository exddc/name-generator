import asyncio
from unittest.mock import AsyncMock

import pytest

from api.utils import MetricsTracker


class FakeTransaction:
    def __init__(self):
        self.connection = object()

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


@pytest.fixture(autouse=True)
def transaction(monkeypatch):
    context = FakeTransaction()
    monkeypatch.setattr("api.utils.in_transaction", lambda: context)
    return context


def test_creative_metrics_store_actual_model_latency_and_cost(monkeypatch, transaction):
    create_metrics = AsyncMock(return_value=object())
    create_generations = AsyncMock()
    monkeypatch.setattr("api.utils.SuggestionMetrics.create", create_metrics)
    monkeypatch.setattr("api.utils.LlmGenerationMetric.bulk_create", create_generations)
    tracker = MetricsTracker(generation_path="lexicon")
    tracker._durations["llm"] = [321.4]
    tracker.record_llm_generation(
        requested_model="openai/gpt-oss-120b",
        actual_model="openai/gpt-oss-120b",
        usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        cost_usd=0.000027,
        latency_ms=321,
        fallback_used=False,
    )

    asyncio.run(tracker.save(suggestion_id=266, requested_count=1))

    stored = create_metrics.call_args.kwargs
    assert stored["generation_path"] == "lexicon"
    assert stored["requested_model"] == "openai/gpt-oss-120b"
    assert stored["actual_model"] == "openai/gpt-oss-120b"
    assert stored["creative_path_duration_ms"] == 321
    assert stored["llm_tokens_total"] == 120
    assert stored["llm_cost_usd"] == 0.000027
    call = create_generations.call_args.args[0][0]
    assert call.actual_model == "openai/gpt-oss-120b"
    assert call.latency_ms == 321
    assert create_metrics.call_args.kwargs["using_db"] is transaction.connection
    assert create_generations.call_args.kwargs["using_db"] is transaction.connection


def test_mixed_model_calls_preserve_exact_per_call_attribution(monkeypatch, transaction):
    create_metrics = AsyncMock(return_value=object())
    create_generations = AsyncMock()
    monkeypatch.setattr("api.utils.SuggestionMetrics.create", create_metrics)
    monkeypatch.setattr("api.utils.LlmGenerationMetric.bulk_create", create_generations)
    tracker = MetricsTracker(generation_path="lexicon")
    tracker._durations["llm"] = [400.0, 600.0]

    tracker.record_llm_generation(
        requested_model="openai/gpt-oss-120b",
        actual_model="openai/gpt-oss-20b",
        usage={"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
        cost_usd=0.000012,
        latency_ms=400,
        fallback_used=True,
    )
    tracker.record_llm_generation(
        requested_model="openai/gpt-oss-120b",
        actual_model="openai/gpt-oss-120b",
        usage={"prompt_tokens": 150, "completion_tokens": 50, "total_tokens": 200},
        cost_usd=0.0000525,
        latency_ms=600,
        fallback_used=False,
    )

    asyncio.run(tracker.save(suggestion_id=267, requested_count=2))

    request_row = create_metrics.call_args.kwargs
    assert request_row["requested_model"] == "openai/gpt-oss-120b"
    assert request_row["actual_model"] == "mixed"
    assert request_row["fallback_used"] is True
    assert request_row["llm_tokens_total"] == 300
    assert request_row["llm_cost_usd"] == 0.0000645
    assert request_row["creative_path_duration_ms"] == 1000

    calls = create_generations.call_args.args[0]
    assert [call.actual_model for call in calls] == [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
    ]
    assert [call.total_tokens for call in calls] == [100, 200]
    assert [float(call.cost_usd) for call in calls] == [0.000012, 0.0000525]
    assert [call.latency_ms for call in calls] == [400, 600]
    assert [call.fallback_used for call in calls] == [True, False]
