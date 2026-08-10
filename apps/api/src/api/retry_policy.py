"""Single documented retry policy: exponential backoff with full jitter.

Worst-case amplification is capped by MAX_SUGGESTIONS_RETRIES (model calls)
and per-request checker-job / candidate budgets. Clients and the API share
the same delay formula so duplicate retries do not stampede dependencies.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


# Policy name returned in structured 429/503 bodies for clients.
POLICY_NAME = "exponential_backoff_jitter"

# Base delay before the first retry (seconds). Attempt 0 is the initial try.
BASE_DELAY_SECONDS = 0.5
# Cap for any single sleep so p95 wait stays bounded under load.
MAX_DELAY_SECONDS = 8.0
# Full jitter: sleep = uniform(0, min(max, base * 2**attempt)).
# See AWS Architecture Blog "Exponential Backoff And Jitter".


@dataclass(frozen=True)
class RetryPolicy:
    """Immutable retry schedule shared by API loops and client guidance."""

    name: str = POLICY_NAME
    base_delay_seconds: float = BASE_DELAY_SECONDS
    max_delay_seconds: float = MAX_DELAY_SECONDS
    # Inclusive max of *retry* sleeps after a failed attempt; model call count
    # is max_attempts = max_retries (configured via MAX_SUGGESTIONS_RETRIES).
    max_retries: int = 5

    def delay_seconds(self, attempt: int, *, rng: random.Random | None = None) -> float:
        """Return full-jitter delay after `attempt` (0-based failed try)."""
        if attempt < 0:
            return 0.0
        ceiling = min(
            self.max_delay_seconds,
            self.base_delay_seconds * (2**attempt),
        )
        picker = rng.random if rng is not None else random.random
        return picker() * ceiling

    def worst_case_model_calls(self) -> int:
        """Upper bound on LLM invocations for one user request."""
        return max(1, self.max_retries)

    def client_guidance(self) -> dict[str, float | int | str]:
        """Structured fields attached to rate-limit / saturation responses."""
        return {
            "retry_policy": self.name,
            "retry_base_delay_seconds": self.base_delay_seconds,
            "retry_max_delay_seconds": self.max_delay_seconds,
            "retry_max_attempts": self.worst_case_model_calls(),
        }


def default_retry_policy(max_retries: int) -> RetryPolicy:
    return RetryPolicy(max_retries=max(1, max_retries))
