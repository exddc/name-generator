# Name Generator — production monitoring (TW-267)

Shared **Uptime Kuma** runs on a separate VPS and is **not** deployed from this repo.
This document is the app-owned contract: what to monitor, which signals are safe, and how to respond.

## Platform (recorded decision)

| Field | Choice |
| --- | --- |
| Platform | Uptime Kuma (self-hosted, shared across projects) |
| Expected cost | $0 software; monitoring VPS + existing Resend usage |
| Ownership | Shared Kuma instance owned by ops; this app owns probe endpoints + canary token |
| Retention | Managed on the monitoring host (≥ 30 days target) |
| Failure domain | Separate VPS from this application stack |

Compared and deferred: OneUptime (heavier), OpenStatus (uptime-focused alternative), incident.io (future IR layer).

**Notifications (configured in shared Kuma, not here):** primary = email via Resend SMTP; optional secondary = Telegram bot (free).

## Application prerequisites

Set on the API host:

```bash
MONITORING_CANARY_TOKEN=<shared-secret>
```

Compose already forwards the variable. Never commit the real token.

## Monitors to create in shared Uptime Kuma

| Name | Type | URL | Interval | Expect |
| --- | --- | --- | --- | --- |
| name-generator-web | HTTP(s) | `https://name-generator.timoweiss.me` | 60s | status 200 |
| name-generator-api-health | HTTP(s) - Json Query | `https://api.name-generator.timoweiss.me/health/` | 60s | status 200; `$.dependencies.database` equal `ok` |
| name-generator-api-degraded | HTTP(s) - Json Query | `https://api.name-generator.timoweiss.me/health/` | 120s | status 200; `$.status` equal `ok` |
| name-generator-gpt-oss-canary | HTTP(s) - Json Query | `https://api.name-generator.timoweiss.me/health/canary` | 900s | status 200; `$.status` equal `ok`; header `X-Canary-Token: <token>` |

Assign Resend email (and optional Telegram) to each monitor; enable **recovery** notifications.

### Severity cheat sheet

| Monitor | Meaning | First response |
| --- | --- | --- |
| web | Public site down | DNS / host / deploy |
| api-health | API or Postgres dependency | API containers, Postgres, recent deploy |
| api-degraded | Usually creative GPT-OSS 120B unavailable | Groq status / permissions; 20B path may still work |
| gpt-oss-canary | Model presence or contract probe failed | `error_class` in canary JSON / `llm_canary_completed` logs — never dump prompts |

## Safe signals (no prompts / credentials)

`/health/canary` and LLM operational logs may include:

- `error_class`: `model_not_found`, `unsupported_parameter`, `timeout`, `connection_error`, `provider_4xx`, `provider_5xx`, `invalid_contract`, `rate_limited`
- `latency_ms`, token counts, `cost_usd`, provider request id / HTTP status / error code

Must never include: user prompts, completion text, API keys, Authorization headers, connection strings.

Health DB failures return exception **type** only.

## Incident response (this app)

1. **Detect** — shared Kuma emails (and optional Telegram) on down.
2. **Acknowledge** — own the alert in inbox / Kuma.
3. **Triage** — which monitor; pull safe `error_class` / latency only.
4. **Mitigate** — restart, roll back, or wait on provider; creative-only issues may leave default generation up.
5. **Recover** — monitors green + recovery notification.
6. **Close** — archive thread; note timings.

Synthetic outage drills are run against shared Kuma (see the monitoring ops repo), not from this codebase.

## Local / Bruno checks

- `GET /health/` — no auth
- `GET /health/canary` with `X-Canary-Token` — Bruno: `GPT-OSS Canary` under Domain Generator (local + Prod)
