# Cost controls, retries, and queue amplification (TW-235)

Public generation is protected with per-identity/IP quotas, per-request budgets,
idempotency, cancellation, global queue backpressure, and an emergency circuit
breaker.

## Retry policy (single)

Name: **`exponential_backoff_jitter`**

| Parameter | Value |
| --- | --- |
| Base delay | `0.5s` |
| Max delay | `8s` |
| Formula | full jitter: `sleep = random() * min(max, base * 2**attempt)` |
| Max model attempts per request | `MAX_SUGGESTIONS_RETRIES` (default `5`) |

Clients receiving **429** or saturated **503** must:

1. Honour `Retry-After` when present.
2. Otherwise apply this policy using `retry_base_delay_seconds` /
   `retry_max_delay_seconds` / `retry_max_attempts` from the error body.
3. Send a stable `Idempotency-Key` so duplicate retries do not re-run work.

Worst-case model calls for one user request: **`max_retries`**.
Worst-case checker jobs for one request: **`MAX_CHECKER_JOBS_PER_REQUEST`**.

Implementation: `apps/api/src/api/retry_policy.py`.

## Quotas (burst + daily)

Charged for generation, similar-names, and variants paths.

| Resource | Anonymous burst | Anonymous daily | Auth burst | Auth daily |
| --- | --- | --- | --- | --- |
| Generation requests | `GENERATION_QUOTA_ANONYMOUS_BURST` (5) | `…_DAILY` (20) | `…_AUTHENTICATED_BURST` (50) | `…_DAILY` (200) |
| Anon network (IP) | `GENERATION_QUOTA_ANONYMOUS_NETWORK_BURST` (20) | `…_DAILY` (100) | — | — |
| Candidates | `CANDIDATES_QUOTA_ANONYMOUS_BURST` (100) | daily (400) | auth burst (400) | daily (4000) |
| Tokens | `TOKENS_QUOTA_ANONYMOUS_BURST` (50k) | daily (200k) | auth burst (200k) | daily (2M) |
| Checker jobs | `CHECKER_JOBS_QUOTA_ANONYMOUS_BURST` (100) | daily (400) | auth burst (400) | daily (4000) |
| Concurrency | `CONCURRENT_GENERATIONS_ANONYMOUS` (1) | | auth (3) | |
| Wall time | `REQUEST_WALL_TIME_SECONDS` (60) per request | | | |

Burst window: `GENERATION_QUOTA_BURST_WINDOW_SECONDS` (default 60s).
Daily window: `GENERATION_QUOTA_DAILY_WINDOW_SECONDS` (default 86400s).

**429** bodies include `retry_after_seconds`, `retry_policy`, `limit`,
`remaining`, and the shared backoff fields. Header: `Retry-After`.

## Backpressure and kill switch

| Control | Env | Default | Effect |
| --- | --- | --- | --- |
| Queue depth | `RQ_MAX_QUEUE_DEPTH` | 500 | Atomic reservation vs LLEN+reserved; over limit → **503** |
| Queue age | `RQ_MAX_QUEUE_AGE_SECONDS` | 60 | Oldest job too old → **503** |
| Kill switch | `EMERGENCY_CIRCUIT_BREAKER` | false | All generation deps return **503** |

Dependency saturation always returns a **stable 503** with `Retry-After` rather
than unbounded queue growth.

## Idempotency

Header: `Idempotency-Key` (scoped per authenticated subject).

- First use: claim `in_progress`, run work once.
- Concurrent duplicate: **429** with short `Retry-After`.
- Completed: replay stored result without LLM/worker fan-out.
- Client cancel: claim abandoned so a real retry can run.

TTL: `IDEMPOTENCY_TTL_SECONDS` (default 86400).

## Cancellation

Streaming endpoints watch `request.is_disconnected()`. On cancel:

1. Pending RQ jobs are cancelled/deleted.
2. Metrics record `client_cancelled`.
3. No successful complete event is emitted; no silent success persist of the run.
4. Idempotency in-progress claims are abandoned.

## Documented load budgets

Under abuse or provider outage, keep:

| Signal | Budget |
| --- | --- |
| Spend amplification | ≤ `max_retries` model calls and ≤ `MAX_CHECKER_JOBS_PER_REQUEST` jobs per request |
| Queue depth | ≤ `RQ_MAX_QUEUE_DEPTH` |
| Queue age | ≤ `RQ_MAX_QUEUE_AGE_SECONDS` |
| Request wall time (p95 target) | ≤ `REQUEST_WALL_TIME_SECONDS` |
| Worker utilization | bounded by concurrency quotas + queue rejection |

Exercise the kill switch by setting `EMERGENCY_CIRCUIT_BREAKER=true` (see unit
test `test_emergency_circuit_breaker_blocks_generation`).

## Client guidance

The web client should:

- Attach a UUID `Idempotency-Key` per user-initiated generation.
- On 429/503, wait using Retry-After or exponential_backoff_jitter.
- Abort streams with `AbortController` so the API marks work obsolete.
