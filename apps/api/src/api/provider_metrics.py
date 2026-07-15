"""Prometheus metrics for the Groq model boundary."""

from prometheus_client import Counter, Gauge, Histogram


MODEL_INFO = Gauge(
    "domain_generator_llm_model_info",
    "Effective LLM model configuration (always 1 for the active profile).",
    ["provider", "model", "profile", "reasoning_effort", "response_format", "stage"],
)

REQUESTS = Counter(
    "domain_generator_llm_requests_total",
    "LLM completion attempts by outcome and classified provider error.",
    ["provider", "model", "outcome", "error_class", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "domain_generator_llm_request_duration_seconds",
    "End-to-end LLM completion latency.",
    ["provider", "model"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30),
)

CANDIDATE_COUNT = Histogram(
    "domain_generator_llm_candidate_batch_size",
    "Schema-valid domain candidates returned by the model.",
    ["provider", "model"],
    buckets=(0, 1, 5, 10, 20, 40, 80, 120),
)

CANDIDATES = Counter(
    "domain_generator_llm_candidates_total",
    "Candidate strings accepted or rejected by semantic domain validation.",
    ["provider", "model", "outcome"],
)

CONTRACT_FAILURES = Counter(
    "domain_generator_llm_contract_failures_total",
    "Responses that failed the configured candidate schema.",
    ["provider", "model", "reason"],
)

FALLBACKS = Counter(
    "domain_generator_llm_fallbacks_total",
    "Model fallbacks. The current cutover deliberately configures no automatic fallback.",
    ["provider", "from_model", "to_model"],
)

STARTUP_VALIDATIONS = Counter(
    "domain_generator_llm_startup_validations_total",
    "Remote model availability checks performed during startup.",
    ["provider", "model", "outcome", "error_class"],
)


def configure_model_info(
    *,
    model: str,
    profile: str,
    reasoning_effort: str,
    response_format: str,
    stage: str,
) -> None:
    """Expose the effective non-secret model configuration."""
    MODEL_INFO.labels(
        provider="groq",
        model=model,
        profile=profile,
        reasoning_effort=reasoning_effort,
        response_format=response_format,
        stage=stage,
    ).set(1)
    # Ensure fallback-rate queries have a zero-valued series before any fallback.
    FALLBACKS.labels(provider="groq", from_model=model, to_model="none").inc(0)
