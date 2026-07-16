import asyncio
import json
import logging
import re
import threading
import time
import traceback
from dataclasses import dataclass, replace
from typing import Optional

import groq
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from api.config import GroqModelProfile, Settings, get_settings
from api.exceptions import GenerationFailedError, RateLimitedError, ServiceUnavailableError
from api.suggestor.base import SuggestorBase
from .prompts import PromptType, SimilarContext, UserPreferences, create_prompt


MAX_RETRIES = 3
RETRY_DELAYS = [0.5, 1.0, 2.0]
logger = logging.getLogger("uvicorn.error")


class CandidateResponse(BaseModel):
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


@dataclass(frozen=True)
class GenerationResult:
    candidates: list[str]
    requested_model: str
    model: str
    profile_name: str
    usage: dict[str, int]
    cost_usd: float
    latency_ms: int
    fallback_used: bool = False


@dataclass(frozen=True)
class ModelAvailability:
    available: bool
    reason: str | None = None
    retry_at: float | None = None


class ModelAvailabilityRegistry:
    """Process-local startup validation state shared by request suggestors."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._models: dict[str, ModelAvailability] = {}
        self._probes_in_progress: set[str] = set()

    def set(
        self,
        model: str,
        available: bool,
        reason: str | None = None,
        retry_after_seconds: float = 0,
    ) -> ModelAvailability:
        with self._lock:
            status = ModelAvailability(
                available=available,
                reason=reason,
                retry_at=(
                    None
                    if available
                    else time.monotonic() + max(0, retry_after_seconds)
                ),
            )
            self._models[model] = status
            self._probes_in_progress.discard(model)
            return status

    def get(self, model: str) -> ModelAvailability | None:
        with self._lock:
            return self._models.get(model)

    def claim_revalidation(self, model: str) -> bool:
        """Allow one caller to probe after the unavailable TTL expires."""
        with self._lock:
            status = self._models.get(model)
            if status is None or status.available:
                return False
            if status.retry_at is not None and time.monotonic() < status.retry_at:
                return False
            if model in self._probes_in_progress:
                return False
            self._probes_in_progress.add(model)
            return True

    def reset(self) -> None:
        with self._lock:
            self._models.clear()
            self._probes_in_progress.clear()


model_availability = ModelAvailabilityRegistry()


def select_model_profile(
    prompt_type: PromptType, settings: Settings | None = None
) -> GroqModelProfile:
    """Select an immutable model profile for this request only."""
    resolved_settings = settings or get_settings()
    if prompt_type is PromptType.LEXICON:
        return resolved_settings.groq_creative_profile
    return resolved_settings.groq_default_profile


def _structured_log(event: str, level: int = logging.INFO, **fields: object) -> None:
    """Log allow-listed operational data without prompts or credentials."""
    logger.log(level, json.dumps({"event": event, **fields}, sort_keys=True))


def _safe_identifier(value: object) -> str | None:
    if not isinstance(value, (str, int)):
        return None
    sanitized = re.sub(r"[^A-Za-z0-9._:/-]", "_", str(value))[:128]
    return sanitized or None


def _safe_error_diagnostics(exc: BaseException, *, include_traceback: bool = False) -> dict[str, object]:
    """Extract operational identifiers without logging messages, prompts, or headers."""
    diagnostics: dict[str, object] = {"exception_type": type(exc).__name__}
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        diagnostics["provider_http_status"] = status_code

    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            provider_code = _safe_identifier(error.get("code") or error.get("type"))
            if provider_code:
                diagnostics["provider_error_code"] = provider_code

    request_id = _safe_identifier(getattr(exc, "request_id", None))
    if not request_id:
        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", {})
        if hasattr(headers, "get"):
            request_id = _safe_identifier(headers.get("x-request-id"))
    if request_id:
        diagnostics["provider_request_id"] = request_id

    if include_traceback:
        diagnostics["traceback"] = [
            {
                "file": frame.filename,
                "line": frame.lineno,
                "function": frame.name,
            }
            for frame in traceback.extract_tb(exc.__traceback__)[-12:]
        ]
    return diagnostics


def _usage_dict(completion: object) -> dict[str, int]:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return {}
    raw = usage.model_dump() if hasattr(usage, "model_dump") else {}
    prompt_details = raw.get("prompt_tokens_details") or {}
    if hasattr(prompt_details, "model_dump"):
        prompt_details = prompt_details.model_dump()
    return {
        "prompt_tokens": int(raw.get("prompt_tokens") or 0),
        "completion_tokens": int(raw.get("completion_tokens") or 0),
        "total_tokens": int(raw.get("total_tokens") or 0),
        "cached_tokens": int(prompt_details.get("cached_tokens") or 0),
    }


def calculate_cost_usd(profile: GroqModelProfile, usage: dict[str, int]) -> float:
    """Estimate provider cost from the configured per-million-token prices."""
    prompt_tokens = usage.get("prompt_tokens", 0)
    cached_tokens = min(prompt_tokens, usage.get("cached_tokens", 0))
    uncached_tokens = prompt_tokens - cached_tokens
    completion_tokens = usage.get("completion_tokens", 0)
    cost = (
        uncached_tokens * profile.input_cost_per_million
        + cached_tokens * profile.cached_input_cost_per_million
        + completion_tokens * profile.output_cost_per_million
    ) / 1_000_000
    return round(cost, 8)


class GroqSuggestor(SuggestorBase):
    def __init__(self, client: groq.Groq | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.api_key = self.settings.groq_api_key
        # Retained for compatibility with callers that inspect the default model.
        self.model = self.settings.groq_model
        self.client = client or groq.Groq(
            api_key=self.api_key,
            timeout=self.settings.groq_model_request_timeout_seconds,
        )

    def _retrieve_exact_model(self, profile: GroqModelProfile) -> str:
        remote_model = self.client.models.retrieve(profile.model)
        effective_model = getattr(remote_model, "id", None)
        if effective_model != profile.model:
            raise RuntimeError(
                f"Groq returned a different model while validating {profile.name}"
            )
        return effective_model

    def validate_model_availability(self) -> dict[str, ModelAvailability]:
        """Validate both models, degrading only the creative capability."""
        results: dict[str, ModelAvailability] = {}
        for profile in (
            self.settings.groq_default_profile,
            self.settings.groq_creative_profile,
        ):
            try:
                effective_model = self._retrieve_exact_model(profile)
            except Exception as exc:
                reason = "startup_validation_failed"
                results[profile.model] = model_availability.set(
                    profile.model,
                    False,
                    reason,
                    retry_after_seconds=(
                        self.settings.groq_creative_revalidation_seconds
                        if profile.name == "creative"
                        else 0
                    ),
                )
                _structured_log(
                    "llm_model_unavailable",
                    logging.ERROR if profile.name == "default" else logging.WARNING,
                    model=profile.model,
                    profile=profile.name,
                    reason=reason,
                    **_safe_error_diagnostics(exc),
                )
                if profile.name == "default":
                    raise
                continue

            results[profile.model] = model_availability.set(profile.model, True)
            _structured_log(
                "llm_model_ready",
                model=profile.model,
                effective_model=effective_model,
                profile=profile.name,
                reasoning_effort=profile.reasoning_effort,
                response_format="json_schema",
                strict_schema=True,
                stream=False,
                include_reasoning=False,
            )
        return results

    async def _ensure_model_available(
        self, profile: GroqModelProfile, prompt_type: PromptType
    ) -> None:
        availability = model_availability.get(profile.model)
        if availability is None or availability.available:
            return

        if not model_availability.claim_revalidation(profile.model):
            _structured_log(
                "llm_request_blocked_model_unavailable",
                logging.WARNING,
                requested_model=profile.model,
                profile=profile.name,
                prompt_type=prompt_type.value,
                reason=availability.reason,
            )
            raise ServiceUnavailableError(
                details=(
                    "Creative generation is temporarily unavailable."
                    if profile.name == "creative"
                    else "AI generation is temporarily unavailable."
                )
            )

        try:
            effective_model = await asyncio.to_thread(
                self._retrieve_exact_model, profile
            )
        except asyncio.CancelledError:
            model_availability.set(
                profile.model,
                False,
                "revalidation_cancelled",
                retry_after_seconds=self.settings.groq_creative_revalidation_seconds,
            )
            raise
        except Exception as exc:
            reason = "revalidation_failed"
            model_availability.set(
                profile.model,
                False,
                reason,
                retry_after_seconds=(
                    self.settings.groq_creative_revalidation_seconds
                    if profile.name == "creative"
                    else 0
                ),
            )
            _structured_log(
                "llm_model_revalidation_failed",
                logging.WARNING,
                model=profile.model,
                profile=profile.name,
                reason=reason,
                **_safe_error_diagnostics(exc),
            )
            raise ServiceUnavailableError(
                details="Creative generation is temporarily unavailable."
            ) from exc

        model_availability.set(profile.model, True)
        _structured_log(
            "llm_model_recovered",
            model=profile.model,
            effective_model=effective_model,
            profile=profile.name,
            prompt_type=prompt_type.value,
        )

    async def generate(
        self,
        description: str,
        count: int = 10,
        prompt_type: PromptType = PromptType.LEGACY,
        preferences: Optional[UserPreferences] = None,
        similar_context: Optional[SimilarContext] = None,
    ) -> GenerationResult:
        """Generate candidates with a request-scoped model selection."""
        started = time.perf_counter()
        primary_profile = select_model_profile(prompt_type, self.settings)

        try:
            await self._ensure_model_available(primary_profile, prompt_type)
            result = await self._generate_with_profile(
                primary_profile,
                description,
                count,
                prompt_type,
                preferences,
                similar_context,
            )
        except (RateLimitedError, ServiceUnavailableError):
            if (
                primary_profile.name != "creative"
                or not self.settings.groq_creative_fallback_to_default
            ):
                _structured_log(
                    "llm_fallback_skipped",
                    logging.WARNING,
                    requested_model=primary_profile.model,
                    fallback_enabled=self.settings.groq_creative_fallback_to_default,
                )
                raise

            fallback_profile = self.settings.groq_default_profile
            _structured_log(
                "llm_fallback_started",
                logging.WARNING,
                requested_model=primary_profile.model,
                fallback_model=fallback_profile.model,
            )
            result = await self._generate_with_profile(
                fallback_profile,
                description,
                count,
                prompt_type,
                preferences,
                similar_context,
            )
            result = replace(
                result,
                requested_model=primary_profile.model,
                fallback_used=True,
            )

        result = replace(result, latency_ms=round((time.perf_counter() - started) * 1000))
        _structured_log(
            "llm_request_completed",
            requested_model=result.requested_model,
            effective_model=result.model,
            profile=result.profile_name,
            prompt_type=prompt_type.value,
            latency_ms=result.latency_ms,
            candidate_count=len(result.candidates),
            prompt_tokens=result.usage.get("prompt_tokens", 0),
            completion_tokens=result.usage.get("completion_tokens", 0),
            total_tokens=result.usage.get("total_tokens", 0),
            cost_usd=result.cost_usd,
            fallback_used=result.fallback_used,
        )
        return result

    async def _generate_with_profile(
        self,
        profile: GroqModelProfile,
        description: str,
        count: int,
        prompt_type: PromptType,
        preferences: Optional[UserPreferences],
        similar_context: Optional[SimilarContext],
    ) -> GenerationResult:
        for attempt in range(MAX_RETRIES):
            delay = RETRY_DELAYS[attempt]
            try:
                return await asyncio.to_thread(
                    self._make_request,
                    profile,
                    description,
                    count,
                    prompt_type,
                    preferences,
                    similar_context,
                )

            except groq.RateLimitError as exc:
                self._log_attempt_error(profile, prompt_type, attempt, "rate_limited", exc)
                if attempt == MAX_RETRIES - 1:
                    raise RateLimitedError(
                        details="AI model is currently overloaded. Please try again in a few moments."
                    )
                delay *= 2

            except groq.APITimeoutError as exc:
                self._log_attempt_error(profile, prompt_type, attempt, "timeout", exc)
                if attempt == MAX_RETRIES - 1:
                    raise ServiceUnavailableError(details="AI service request timed out.")

            except groq.APIConnectionError as exc:
                self._log_attempt_error(profile, prompt_type, attempt, "connection_error", exc)
                if attempt == MAX_RETRIES - 1:
                    raise ServiceUnavailableError(details="Unable to connect to the AI service.")

            except groq.APIStatusError as exc:
                error_class = "provider_4xx" if 400 <= exc.status_code < 500 else "provider_5xx"
                self._log_attempt_error(profile, prompt_type, attempt, error_class, exc)
                if exc.status_code == 403 and profile.name == "creative":
                    model_availability.set(
                        profile.model,
                        False,
                        "provider_permission_denied",
                        retry_after_seconds=self.settings.groq_creative_revalidation_seconds,
                    )
                    raise ServiceUnavailableError(
                        details="Creative generation is temporarily unavailable."
                    )
                if 400 <= exc.status_code < 500:
                    raise GenerationFailedError(
                        details="The AI provider rejected the configured model profile."
                    )
                if attempt == MAX_RETRIES - 1:
                    raise ServiceUnavailableError(details="AI service is temporarily unavailable.")

            except (ValidationError, ValueError) as exc:
                self._log_attempt_error(profile, prompt_type, attempt, "invalid_contract", exc)
                if attempt == MAX_RETRIES - 1:
                    break

            except Exception as exc:
                self._log_attempt_error(
                    profile,
                    prompt_type,
                    attempt,
                    "unexpected",
                    exc,
                    include_traceback=True,
                )
                raise GenerationFailedError(
                    details="Unable to generate domain suggestions due to an internal error."
                ) from exc

            await asyncio.sleep(delay)

        raise GenerationFailedError(
            details="Unable to generate domain suggestions after multiple attempts."
        )

    def _log_attempt_error(
        self,
        profile: GroqModelProfile,
        prompt_type: PromptType,
        attempt: int,
        error_class: str,
        exc: BaseException,
        *,
        include_traceback: bool = False,
    ) -> None:
        _structured_log(
            "llm_request_failed",
            logging.WARNING,
            model=profile.model,
            profile=profile.name,
            prompt_type=prompt_type.value,
            attempt=attempt + 1,
            error_class=error_class,
            **_safe_error_diagnostics(exc, include_traceback=include_traceback),
        )

    def _make_request(
        self,
        profile: GroqModelProfile,
        description: str,
        count: int,
        prompt_type: PromptType,
        preferences: Optional[UserPreferences] = None,
        similar_context: Optional[SimilarContext] = None,
    ) -> GenerationResult:
        prompt = create_prompt(
            prompt_type,
            description,
            count + 10,
            preferences=preferences,
            similar_context=similar_context,
        )
        completion = self.client.chat.completions.create(
            model=profile.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=profile.temperature,
            max_completion_tokens=profile.max_completion_tokens,
            top_p=profile.top_p,
            reasoning_effort=profile.reasoning_effort,
            include_reasoning=False,
            stream=False,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "domain_candidates",
                    "strict": True,
                    "schema": CANDIDATE_JSON_SCHEMA,
                },
            },
        )
        content = completion.choices[0].message.content
        if not isinstance(content, str):
            raise ValueError("Model response did not contain text content")

        candidates = CandidateResponse.model_validate_json(content).candidates
        sanitized = [candidate.strip().lower().replace(" ", "") for candidate in candidates]
        usage = _usage_dict(completion)
        return GenerationResult(
            candidates=list(dict.fromkeys(sanitized)),
            requested_model=profile.model,
            model=getattr(completion, "model", None) or profile.model,
            profile_name=profile.name,
            usage=usage,
            cost_usd=calculate_cost_usd(profile, usage),
            latency_ms=0,
        )
