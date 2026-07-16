import asyncio
import os

import pytest

from api.suggestor.groq import GroqSuggestor
from api.suggestor.prompts import PromptType


@pytest.mark.skipif(
    os.getenv("RUN_GROQ_CONTRACT_TEST") != "1",
    reason="set RUN_GROQ_CONTRACT_TEST=1 to call the production Groq model",
)
def test_gpt_oss_20b_returns_schema_valid_domain_candidates():
    suggestor = GroqSuggestor()

    suggestor.validate_model_availability()
    result = asyncio.run(
        suggestor.generate(
            "A privacy-first collaborative writing application for small teams",
            count=5,
        )
    )

    assert suggestor.model == "openai/gpt-oss-20b"
    assert result.model == "openai/gpt-oss-20b"
    assert len(result.candidates) >= 5
    assert all(isinstance(candidate, str) and "." in candidate for candidate in result.candidates)


@pytest.mark.skipif(
    os.getenv("RUN_GROQ_CONTRACT_TEST") != "1",
    reason="set RUN_GROQ_CONTRACT_TEST=1 to call the production Groq model",
)
def test_gpt_oss_120b_creative_profile_returns_schema_valid_candidates():
    suggestor = GroqSuggestor()

    result = asyncio.run(
        suggestor.generate(
            "A privacy-first collaborative writing application for small teams",
            count=5,
            prompt_type=PromptType.LEXICON,
        )
    )

    assert result.requested_model == "openai/gpt-oss-120b"
    assert result.model == "openai/gpt-oss-120b"
    assert not result.fallback_used
    assert len(result.candidates) >= 5
    assert all(isinstance(candidate, str) and "." in candidate for candidate in result.candidates)
