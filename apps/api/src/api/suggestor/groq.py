from typing import List, Optional
import groq
import json
import asyncio

from api.config import get_settings
from api.suggestor.base import SuggestorBase
from api.exceptions import GenerationFailedError, ServiceUnavailableError, RateLimitedError
from .prompts import create_prompt, PromptType, UserPreferences, SimilarContext


# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [0.5, 1.0, 2.0]


class GroqSuggestor(SuggestorBase):
    def __init__(self):
        self.api_key = get_settings().groq_api_key
        self.model = get_settings().groq_model
        self.model_reasoning_effort = get_settings().groq_model_reasoning_effort
        self.model_stream = get_settings().groq_model_stream
        self.model_temperature = get_settings().groq_model_temperature
        self.model_max_completion_tokens = get_settings().groq_model_max_completion_tokens
        self.model_top_p = get_settings().groq_model_top_p

        self.client = groq.Groq(api_key=self.api_key)

    async def generate(
        self,
        description: str,
        count: int = 10,
        prompt_type: PromptType = PromptType.LEGACY,
        preferences: Optional[UserPreferences] = None,
        similar_context: Optional[SimilarContext] = None,
    ) -> List[str]:
        """Generate domain suggestions using the specified prompt type.
        
        Args:
            description: User's description of what they're looking for
            count: Number of suggestions to generate
            prompt_type: The type of prompt to use
            preferences: User preferences for personalized prompts
            similar_context: Context for similar domain generation
        
        Returns:
            List of domain name suggestions
        """
        last_error = None
        
        for attempt in range(MAX_RETRIES):
            try:
                suggestions = await self._make_request(
                    description, count, prompt_type, preferences, similar_context
                )
                if suggestions:
                    return suggestions
                    
                # Empty response - retry
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue
                    
            except groq.RateLimitError as e:
                print(f"[GroqSuggestor] Rate limited (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt] * 2)  # Longer delay for rate limits
                    continue
                raise RateLimitedError(details="AI model is currently overloaded. Please try again in a few moments.")
                
            except groq.APIConnectionError as e:
                print(f"[GroqSuggestor] Connection error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue
                raise ServiceUnavailableError(details="Unable to connect to the AI service.")
                
            except groq.APITimeoutError as e:
                print(f"[GroqSuggestor] Timeout (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue
                raise ServiceUnavailableError(details="AI service request timed out.")
                
            except groq.APIStatusError as e:
                print(f"[GroqSuggestor] API status error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                last_error = e
                # Don't retry on client errors (4xx except 429)
                if 400 <= e.status_code < 500 and e.status_code != 429:
                    raise GenerationFailedError(details=f"API error: {e.message}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue
                raise ServiceUnavailableError(details="AI service is temporarily unavailable.")
                
            except json.JSONDecodeError as e:
                print(f"[GroqSuggestor] JSON parse error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue
                    
            except Exception as e:
                print(f"[GroqSuggestor] Unexpected error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])
                    continue
        
        # All retries exhausted
        print(f"[GroqSuggestor] All {MAX_RETRIES} attempts failed. Last error: {last_error}")
        raise GenerationFailedError(details="Unable to generate domain suggestions after multiple attempts.")

    async def _make_request(
        self,
        description: str,
        count: int,
        prompt_type: PromptType,
        preferences: Optional[UserPreferences] = None,
        similar_context: Optional[SimilarContext] = None,
    ) -> List[str]:
        """Make a single request to the Groq API."""
        prompt = create_prompt(
            prompt_type,
            description,
            count + 10,
            preferences=preferences,
            similar_context=similar_context,
        )
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=self.model_temperature,
            max_completion_tokens=self.model_max_completion_tokens,
            top_p=self.model_top_p,
            reasoning_effort=self.model_reasoning_effort,
            stream=self.model_stream,
            stop=None
        )

        content = completion.choices[0].message.content.strip()
        
        if content.startswith("```json"):
            content = content[len("```json"):].strip()
            if content.endswith("```"):
                content = content[:-len("```")].strip()
            suggestions = json.loads(content)
        elif content.startswith("["):
            suggestions = json.loads(content)
        else:
            suggestions = [content]

        if not isinstance(suggestions, list) or not all(
            isinstance(s, str) for s in suggestions
        ):
            raise ValueError("Model did not return a valid list of strings.")

        # Sanitize suggestions
        sanitized_suggestions = []
        for suggestion in suggestions:
            s = suggestion.strip().lower().replace(" ", "")
            sanitized_suggestions.append(s)

        # Remove duplicates
        sanitized_suggestions = list(set(sanitized_suggestions))

        return sanitized_suggestions