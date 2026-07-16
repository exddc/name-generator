import pytest
from pydantic import ValidationError

from api.config import Settings


def settings_for_model(**overrides) -> Settings:
    values = {
        "groq_api_key": "test-key",
        "groq_model": "openai/gpt-oss-20b",
        "groq_model_reasoning_effort": "low",
        "groq_model_stream": False,
        "groq_creative_model": "openai/gpt-oss-120b",
        "groq_creative_model_reasoning_effort": "low",
        "groq_creative_model_stream": False,
        "groq_validate_model_on_startup": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_gpt_oss_20b_accepts_supported_configuration():
    settings = settings_for_model()

    assert settings.groq_model == "openai/gpt-oss-20b"


@pytest.mark.parametrize("reasoning_effort", ["none", "default", "minimal"])
def test_gpt_oss_20b_rejects_unsupported_reasoning(reasoning_effort: str):
    with pytest.raises(ValidationError, match="must be one of: high, low, medium"):
        settings_for_model(groq_model_reasoning_effort=reasoning_effort)


def test_default_configuration_rejects_a_different_model():
    with pytest.raises(ValidationError, match="GROQ_MODEL must be openai/gpt-oss-20b"):
        settings_for_model(groq_model="openai/gpt-oss-120b")


def test_creative_configuration_requires_120b():
    with pytest.raises(ValidationError, match="GROQ_CREATIVE_MODEL must be openai/gpt-oss-120b"):
        settings_for_model(groq_creative_model="openai/gpt-oss-20b")


def test_creative_profile_rejects_provider_streaming():
    with pytest.raises(ValidationError, match="GROQ_CREATIVE_MODEL_STREAM must be false"):
        settings_for_model(groq_creative_model_stream=True)


def test_non_streaming_client_rejects_stream_configuration():
    with pytest.raises(ValidationError, match="GROQ_MODEL_STREAM must be false"):
        settings_for_model(groq_model_stream=True)


def test_creative_revalidation_ttl_must_not_be_negative():
    with pytest.raises(
        ValidationError, match="GROQ_CREATIVE_REVALIDATION_SECONDS must not be negative"
    ):
        settings_for_model(groq_creative_revalidation_seconds=-1)
