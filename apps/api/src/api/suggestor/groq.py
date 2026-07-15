import asyncio
import json
import logging
import re
import time
from typing import List, Optional

import groq
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from api.config import get_settings
from api.exceptions import GenerationFailedError, RateLimitedError, ServiceUnavailableError
from api.provider_metrics import (
    CANDIDATE_COUNT,
    CANDIDATES,
    CONTRACT_FAILURES,
    REQUEST_LATENCY,
    REQUESTS,
    STARTUP_VALIDATIONS,
    configure_model_info,
)
from api.suggestor.base import SuggestorBase
from .prompts import PromptType, SimilarContext, UserPreferences, create_prompt


MAX_RETRIES = 3
RETRY_DELAYS = [0.5, 1.0, 2.0]
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)
DOMAIN_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9-]{2,63})+$"
)


class CandidateResponse(BaseModel):
    """The only response shape consumed by the suggestion client."""

    model_config = ConfigDict(strict=True)
    candidates: list[str] = Field(min_length=1)

    @field_validator("candidates")
    @classmethod
    def candidates_must_not_be_blank(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("candidate values must not be blank")
        return values


CANDIDATE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 200,
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}


def _structured_log(event: str, level: int = logging.INFO, **fields: object) -> None:
    """Log only allow-listed operational fields; prompts and credentials never enter fields."""
    logger.log(level, json.dumps({"event": event, **fields}, sort_keys=True))


def _classify_api_error(status_code: int, message: str = "") -> str:
    normalized = message.lower()
    if status_code == 404 or "model_not_found" in normalized or "model does not exist" in normalized:
        return "model_not_found"
    if status_code == 403 and ("model" in normalized or "permission" in normalized):
        return "model_unavailable"
    if status_code in {400, 422} and any(
        marker in normalized
        for marker in ("parameter", "reasoning_effort", "response_format", "unsupported")
    ):
        return "unsupported_parameter"
    if status_code == 429:
        return "rate_limited"
    if status_code >= 500:
        return "provider_5xx"
    return "provider_4xx"


class GroqSuggestor(SuggestorBase):
    def __init__(self, client: groq.Groq | None = None):
        settings = get_settings()
        self.api_key = settings.groq_api_key
        self.profile_name = settings.groq_model_profile
        self.profile = settings.groq_profile
        self.model = settings.groq_model
        self.model_reasoning_effort = settings.groq_model_reasoning_effort
        self.model_temperature = settings.groq_model_temperature
        self.model_max_completion_tokens = settings.groq_model_max_completion_tokens
        self.model_top_p = settings.groq_model_top_p
        self.model_request_timeout_seconds = settings.groq_model_request_timeout_seconds
        self.deployment_stage = settings.groq_deployment_stage

        self.client = client or groq.Groq(
            api_key=self.api_key,
            timeout=self.model_request_timeout_seconds,
        )
        configure_model_info(
            model=self.model,
            profile=self.profile_name,
            reasoning_effort=self.model_reasoning_effort,
            response_format=self.profile.response_format,
            stage=self.deployment_stage,
        )

    def validate_model_availability(self) -> None:
        """Fail startup if Groq cannot serve the exact configured model ID."""
        try:
            remote_model = self.client.models.retrieve(self.model)
            effective_model = getattr(remote_model, "id", None)
            if effective_model != self.model:
                raise RuntimeError("Groq returned a different model than the configured model")
        except groq.APIStatusError as exc:
            error_class = _classify_api_error(exc.status_code, exc.message)
            STARTUP_VALIDATIONS.labels(
                provider="groq",
                model=self.model,
                outcome="error",
                error_class=error_class,
            ).inc()
            _structured_log(
                "llm_model_validation_failed",
                logging.ERROR,
                provider="groq",
                model=self.model,
                profile=self.profile_name,
                error_class=error_class,
                status_code=exc.status_code,
            )
            raise RuntimeError(
                f"Configured Groq model is unavailable ({error_class}, status={exc.status_code})"
            ) from exc
        except (groq.APIConnectionError, groq.APITimeoutError) as exc:
            error_class = "timeout" if isinstance(exc, groq.APITimeoutError) else "connection_error"
            STARTUP_VALIDATIONS.labels(
                provider="groq",
                model=self.model,
                outcome="error",
                error_class=error_class,
            ).inc()
            _structured_log(
                "llm_model_validation_failed",
                logging.ERROR,
                provider="groq",
                model=self.model,
                profile=self.profile_name,
                error_class=error_class,
                status_code=0,
            )
            raise RuntimeError(f"Could not validate configured Groq model ({error_class})") from exc

        STARTUP_VALIDATIONS.labels(
            provider="groq",
            model=self.model,
            outcome="success",
            error_class="none",
        ).inc()
        _structured_log(
            "llm_model_ready",
            provider="groq",
            model=self.model,
            effective_model=effective_model,
            profile=self.profile_name,
            reasoning_effort=self.model_reasoning_effort,
            response_format=self.profile.response_format,
            stream=False,
            include_reasoning=False,
            stage=self.deployment_stage,
        )

    async def generate(
        self,
        description: str,
        count: int = 10,
        prompt_type: PromptType = PromptType.LEGACY,
        preferences: Optional[UserPreferences] = None,
        similar_context: Optional[SimilarContext] = None,
    ) -> List[str]:
        """Generate schema-validated domain candidates without logging user input."""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            started = time.perf_counter()
            try:
                suggestions, effective_model, usage = await asyncio.to_thread(
                    self._make_request,
                    description,
                    count,
                    prompt_type,
                    preferences,
                    similar_context,
                )
                REQUEST_LATENCY.labels(provider="groq", model=self.model).observe(
                    time.perf_counter() - started
                )
                REQUESTS.labels(
                    provider="groq",
                    model=self.model,
                    outcome="success",
                    error_class="none",
                    status_code="200",
                ).inc()
                CANDIDATE_COUNT.labels(provider="groq", model=self.model).observe(len(suggestions))
                _structured_log(
                    "llm_request_completed",
                    provider="groq",
                    model=self.model,
                    effective_model=effective_model,
                    profile=self.profile_name,
                    attempt=attempt + 1,
                    latency_ms=round((time.perf_counter() - started) * 1000),
                    candidate_count=len(suggestions),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                )
                return suggestions

            except groq.RateLimitError as exc:
                last_error = exc
                self._record_request_error("rate_limited", exc.status_code, attempt)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt] * 2)
                    continue
                raise RateLimitedError(
                    details="AI model is currently overloaded. Please try again in a few moments."
                )

            except groq.APITimeoutError as exc:
                last_error = exc
                self._record_request_error("timeout", 0, attempt)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue
                raise ServiceUnavailableError(details="AI service request timed out.")

            except groq.APIConnectionError as exc:
                last_error = exc
                self._record_request_error("connection_error", 0, attempt)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue
                raise ServiceUnavailableError(details="Unable to connect to the AI service.")

            except groq.APIStatusError as exc:
                last_error = exc
                error_class = _classify_api_error(exc.status_code, exc.message)
                self._record_request_error(error_class, exc.status_code, attempt)
                if 400 <= exc.status_code < 500 and exc.status_code != 429:
                    raise GenerationFailedError(
                        details="The AI provider rejected the configured model profile."
                    )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue
                raise ServiceUnavailableError(details="AI service is temporarily unavailable.")

            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                CONTRACT_FAILURES.labels(
                    provider="groq", model=self.model, reason="invalid_candidate_schema"
                ).inc()
                self._record_request_error("invalid_contract", 0, attempt)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue

            except Exception as exc:
                last_error = exc
                self._record_request_error("unexpected", 0, attempt)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue

        _structured_log(
            "llm_request_exhausted",
            logging.ERROR,
            provider="groq",
            model=self.model,
            profile=self.profile_name,
            attempts=MAX_RETRIES,
            final_error_class=type(last_error).__name__ if last_error else "unknown",
        )
        raise GenerationFailedError(
            details="Unable to generate domain suggestions after multiple attempts."
        )

    def _record_request_error(self, error_class: str, status_code: int, attempt: int) -> None:
        REQUESTS.labels(
            provider="groq",
            model=self.model,
            outcome="error",
            error_class=error_class,
            status_code=str(status_code),
        ).inc()
        _structured_log(
            "llm_request_failed",
            logging.WARNING,
            provider="groq",
            model=self.model,
            profile=self.profile_name,
            attempt=attempt + 1,
            error_class=error_class,
            status_code=status_code,
        )

    def _request_parameters(self, prompt: str) -> dict:
        parameters = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.model_temperature,
            "max_completion_tokens": self.model_max_completion_tokens,
            "top_p": self.model_top_p,
            "reasoning_effort": self.model_reasoning_effort,
            "stream": False,
        }

        if self.profile.response_format == "json_schema":
            if self.profile.supports_include_reasoning:
                parameters["include_reasoning"] = False
            parameters["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "domain_candidates",
                    "strict": True,
                    "schema": CANDIDATE_JSON_SCHEMA,
                },
            }
        else:
            parameters["response_format"] = {"type": "json_object"}

        return parameters

    def _make_request(
        self,
        description: str,
        count: int,
        prompt_type: PromptType,
        preferences: Optional[UserPreferences] = None,
        similar_context: Optional[SimilarContext] = None,
    ) -> tuple[list[str], str, dict[str, int]]:
        prompt = create_prompt(
            prompt_type,
            description,
            count + 10,
            preferences=preferences,
            similar_context=similar_context,
        )
        completion = self.client.chat.completions.create(**self._request_parameters(prompt))
        content = completion.choices[0].message.content
        if not isinstance(content, str):
            raise ValueError("Model response did not contain text content")

        response = CandidateResponse.model_validate_json(content)
        sanitized = [candidate.strip().lower().replace(" ", "") for candidate in response.candidates]
        unique_candidates = list(dict.fromkeys(sanitized))
        valid_candidates = [
            candidate for candidate in unique_candidates if DOMAIN_PATTERN.fullmatch(candidate)
        ]
        rejected_count = len(unique_candidates) - len(valid_candidates)
        CANDIDATES.labels(provider="groq", model=self.model, outcome="accepted").inc(
            len(valid_candidates)
        )
        CANDIDATES.labels(provider="groq", model=self.model, outcome="rejected").inc(
            rejected_count
        )
        if rejected_count:
            _structured_log(
                "llm_candidates_rejected",
                logging.WARNING,
                provider="groq",
                model=self.model,
                rejected_count=rejected_count,
            )
        if not valid_candidates:
            raise ValueError("Model returned no usable candidates")

        usage = completion.usage.model_dump() if completion.usage else {}
        return valid_candidates, completion.model or self.model, usage
