from typing import List
import groq
import json

from api.config import get_settings
from api.suggestor.base import SuggestorBase
from .prompts import create_prompt, PromptType



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

    async def generate(self, description: str, count: int = 10) -> List[str]:
        try:
            completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
            {
                "role": "user",
                "content": create_prompt(PromptType.LEGACY, description, count + 10)
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
        except Exception as e:
            print(f"Error while generating domain suggestions: {e}")
            return []