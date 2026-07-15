import asyncio
import logging
from typing import List, Optional

import groq
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from api.config import get_settings
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


class GroqSuggestor(SuggestorBase):
    def __init__(self, client: groq.Groq | None = None):
        settings = get_settings()
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.model_reasoning_effort = settings.groq_model_reasoning_effort
        self.model_temperature = settings.groq_model_temperature
        self.model_max_completion_tokens = settings.groq_model_max_completion_tokens
        self.model_top_p = settings.groq_model_top_p
        self.client = client or groq.Groq(
            api_key=self.api_key,
            timeout=settings.groq_model_request_timeout_seconds,
        )

    def validate_model_availability(self) -> None:
        """Fail startup if Groq cannot serve the configured model."""
        remote_model = self.client.models.retrieve(self.model)
        effective_model = getattr(remote_model, "id", None)
        if effective_model != self.model:
            raise RuntimeError("Groq returned a different model than the configured model")

        logger.info(
            "Groq model ready model=%s effective_model=%s reasoning_effort=%s "
            "response_format=json_schema stream=false",
            self.model,
            effective_model,
            self.model_reasoning_effort,
        )

    async def generate(
        self,
        description: str,
        count: int = 10,
        prompt_type: PromptType = PromptType.LEGACY,
        preferences: Optional[UserPreferences] = None,
        similar_context: Optional[SimilarContext] = None,
    ) -> List[str]:
        """Generate schema-validated domain candidates."""
        for attempt in range(MAX_RETRIES):
            delay = RETRY_DELAYS[attempt]
            try:
                suggestions = await asyncio.to_thread(
                    self._make_request,
                    description,
                    count,
                    prompt_type,
                    preferences,
                    similar_context,
                )
                return suggestions

            except groq.RateLimitError:
                if attempt == MAX_RETRIES - 1:
                    raise RateLimitedError(
                        details="AI model is currently overloaded. Please try again in a few moments."
                    )
                delay *= 2

            except groq.APITimeoutError:
                if attempt == MAX_RETRIES - 1:
                    raise ServiceUnavailableError(details="AI service request timed out.")

            except groq.APIConnectionError:
                if attempt == MAX_RETRIES - 1:
                    raise ServiceUnavailableError(details="Unable to connect to the AI service.")

            except groq.APIStatusError as exc:
                if 400 <= exc.status_code < 500:
                    raise GenerationFailedError(
                        details="The AI provider rejected the configured model."
                    )
                if attempt == MAX_RETRIES - 1:
                    raise ServiceUnavailableError(details="AI service is temporarily unavailable.")

            except (ValidationError, ValueError):
                if attempt == MAX_RETRIES - 1:
                    break

            except Exception:
                if attempt == MAX_RETRIES - 1:
                    break

            await asyncio.sleep(delay)

        raise GenerationFailedError(
            details="Unable to generate domain suggestions after multiple attempts."
        )

    def _make_request(
        self,
        description: str,
        count: int,
        prompt_type: PromptType,
        preferences: Optional[UserPreferences] = None,
        similar_context: Optional[SimilarContext] = None,
    ) -> list[str]:
        prompt = create_prompt(
            prompt_type,
            description,
            count + 10,
            preferences=preferences,
            similar_context=similar_context,
        )
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.model_temperature,
            max_completion_tokens=self.model_max_completion_tokens,
            top_p=self.model_top_p,
            reasoning_effort=self.model_reasoning_effort,
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
        return list(dict.fromkeys(sanitized))
