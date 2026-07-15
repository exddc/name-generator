"""Run the versioned TW-228 Qwen/GPT-OSS production-like contract benchmark."""

import json
import os
import re
import statistics
import time
from dataclasses import dataclass

from groq import Groq

from api.suggestor.groq import CANDIDATE_JSON_SCHEMA, CandidateResponse
from api.suggestor.prompts import PromptType, create_prompt


PROMPT_SET_VERSION = "tw-228-v1"
PROMPTS = (
    "A privacy-first collaborative writing app for small teams",
    "A neighborhood bakery in Berlin focused on sourdough and seasonal pastries",
    "An AI tool that organizes academic research notes",
    "A mobile fitness coach for busy parents",
    "A marketplace for refurbished analog cameras",
)
REQUESTED_CANDIDATES = 10
DOMAIN_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9-]{2,63})+$")


@dataclass(frozen=True)
class BenchmarkProfile:
    model: str
    reasoning_effort: str
    response_format: dict
    input_cost_per_million: float
    output_cost_per_million: float
    include_reasoning: bool | None = None


PROFILES = (
    BenchmarkProfile(
        model="qwen/qwen3-32b",
        reasoning_effort="none",
        response_format={"type": "json_object"},
        input_cost_per_million=0.29,
        output_cost_per_million=0.59,
    ),
    BenchmarkProfile(
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "domain_candidates",
                "strict": True,
                "schema": CANDIDATE_JSON_SCHEMA,
            },
        },
        input_cost_per_million=0.075,
        output_cost_per_million=0.30,
        include_reasoning=False,
    ),
)


def percentile(values: list[float], percentage: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentage)
    return ordered[index]


def run_profile(client: Groq, profile: BenchmarkProfile) -> dict:
    latencies: list[float] = []
    total_candidates = 0
    valid_candidates = 0
    unique_candidates: set[str] = set()
    schema_valid_responses = 0
    prompt_tokens = 0
    completion_tokens = 0

    for description in PROMPTS:
        prompt = create_prompt(PromptType.LEGACY, description, REQUESTED_CANDIDATES + 10)
        parameters = {
            "model": profile.model,
            "messages": [{"role": "user", "content": prompt}],
            "reasoning_effort": profile.reasoning_effort,
            "stream": False,
            "temperature": 0.6,
            "max_completion_tokens": 4096,
            "top_p": 0.95,
            "response_format": profile.response_format,
        }
        if profile.include_reasoning is not None:
            parameters["include_reasoning"] = profile.include_reasoning

        started = time.perf_counter()
        completion = client.chat.completions.create(**parameters)
        latencies.append((time.perf_counter() - started) * 1000)
        response = CandidateResponse.model_validate_json(completion.choices[0].message.content)
        schema_valid_responses += 1

        candidates = [candidate.strip().lower().replace(" ", "") for candidate in response.candidates]
        total_candidates += len(candidates)
        valid_candidates += sum(bool(DOMAIN_PATTERN.fullmatch(candidate)) for candidate in candidates)
        unique_candidates.update(candidates)
        if completion.usage:
            prompt_tokens += completion.usage.prompt_tokens
            completion_tokens += completion.usage.completion_tokens

    estimated_cost = (
        prompt_tokens * profile.input_cost_per_million
        + completion_tokens * profile.output_cost_per_million
    ) / 1_000_000
    return {
        "model": profile.model,
        "reasoning_effort": profile.reasoning_effort,
        "requests": len(PROMPTS),
        "schema_valid_responses": schema_valid_responses,
        "total_candidates": total_candidates,
        "valid_domain_rate": round(valid_candidates / max(total_candidates, 1), 4),
        "unique_candidate_rate": round(len(unique_candidates) / max(total_candidates, 1), 4),
        "latency_ms": {
            "mean": round(statistics.mean(latencies)),
            "p50": round(percentile(latencies, 0.5)),
            "p95": round(percentile(latencies, 0.95)),
        },
        "tokens": {"input": prompt_tokens, "output": completion_tokens},
        "estimated_cost_usd": round(estimated_cost, 6),
    }


def main() -> None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY is required")

    client = Groq(api_key=api_key, timeout=30)
    report = {
        "prompt_set_version": PROMPT_SET_VERSION,
        "requested_candidates_per_prompt": REQUESTED_CANDIDATES,
        "results": [run_profile(client, profile) for profile in PROFILES],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
