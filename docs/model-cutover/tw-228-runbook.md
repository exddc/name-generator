# TW-228 canary and rollback runbook

## Effective candidate configuration

```text
GROQ_MODEL_PROFILE=gpt-oss-20b
GROQ_MODEL=openai/gpt-oss-20b
GROQ_MODEL_REASONING_EFFORT=low
GROQ_MODEL_STREAM=false
GROQ_MODEL_INCLUDE_REASONING=false
GROQ_MODEL_RESPONSE_FORMAT=json_schema
GROQ_MODEL_TEMPERATURE=0.6
GROQ_MODEL_MAX_COMPLETION_TOKENS=4096
GROQ_MODEL_TOP_P=0.95
GROQ_MODEL_REQUEST_TIMEOUT_SECONDS=15
GROQ_VALIDATE_MODEL_ON_STARTUP=true
```

Each API process retrieves the exact model ID during startup. A missing key,
unknown model, permission block, model/profile mismatch, unsupported reasoning
value, response-format mismatch, or enabled provider stream prevents the
process from becoming ready. The startup and request logs contain model,
profile, response shape, latency, token counts, and classified errors only;
they never contain prompts or credentials.

## Canary sequence

1. Deploy one canary replica with `GROQ_DEPLOYMENT_STAGE=canary` and send 5% of
   suggestion traffic to it for at least 30 minutes.
2. Confirm `domain_generator_llm_model_info` reports
   `model="openai/gpt-oss-20b"`, the live contract test passes, and no stop
   criterion fires.
3. Increase to 25% for 30 minutes, then 100%. Keep the previous deployment
   available until the 100% stage has remained healthy for one hour.

Stop immediately for model-not-found, model permission/unavailability,
unsupported-parameter 400/422, a schema contract failure, or a missing
effective-model series. Stop after the alert window for any of:

- fallback rate above 1% for 10 minutes;
- provider error rate above 0.5% for 5 minutes;
- domain-candidate rejection rate above 10% for 10 minutes;
- model p95 latency above 5 seconds for 10 minutes;
- API resident memory above 1 GiB for 15 minutes.

Prometheus rules are versioned in `monitoring/model-alerts.yaml`. The
application exposes them and the effective model at `/internal/metrics`.

## Rollback

After 2026-07-17, switch the whole service to the tested GPT-OSS 120B emergency
profile and redeploy:

```text
GROQ_MODEL_PROFILE=gpt-oss-120b-emergency
GROQ_MODEL=openai/gpt-oss-120b
GROQ_MODEL_REASONING_EFFORT=low
GROQ_MODEL_RESPONSE_FORMAT=json_schema
```

All other model settings remain unchanged. Startup must retrieve 120B before
the replica becomes ready. Confirm `domain_generator_llm_model_info` changes to
120B and the live contract passes, then drain 20B replicas.

Before Qwen's 2026-07-17 shutdown only, `qwen3-32b-rollback` plus
`qwen/qwen3-32b`, `reasoning_effort=none`, and `response_format=json_object`
is the versioned baseline rollback. Do not use it after shutdown.

The 20B, pre-shutdown Qwen, and post-shutdown 120B profiles were all retrieved
and exercised successfully through `GroqSuggestor` on 2026-07-15.

