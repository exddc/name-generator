import pytest
from pydantic import ValidationError

from api.config import Settings


def settings_for_profile(**overrides) -> Settings:
    values = {
        "groq_api_key": "test-key",
        "groq_model_profile": "gpt-oss-20b",
        "groq_model": "openai/gpt-oss-20b",
        "groq_model_reasoning_effort": "low",
        "groq_model_stream": False,
        "groq_model_include_reasoning": False,
        "groq_model_response_format": "json_schema",
        "groq_validate_model_on_startup": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_gpt_oss_profile_accepts_supported_configuration():
    settings = settings_for_profile()

    assert settings.groq_model == "openai/gpt-oss-20b"
    assert settings.groq_profile.response_format == "json_schema"


@pytest.mark.parametrize("reasoning_effort", ["none", "default", "minimal"])
def test_gpt_oss_profile_rejects_unsupported_reasoning(reasoning_effort: str):
    with pytest.raises(ValidationError, match="must be one of: high, low, medium"):
        settings_for_profile(groq_model_reasoning_effort=reasoning_effort)


def test_profile_rejects_a_mismatched_model():
    with pytest.raises(ValidationError, match="requires GROQ_MODEL=openai/gpt-oss-20b"):
        settings_for_profile(groq_model="openai/gpt-oss-120b")


def test_non_streaming_client_rejects_stream_configuration():
    with pytest.raises(ValidationError, match="GROQ_MODEL_STREAM must be false"):
        settings_for_profile(groq_model_stream=True)


def test_client_rejects_reasoning_output_it_does_not_consume():
    with pytest.raises(ValidationError, match="GROQ_MODEL_INCLUDE_REASONING must be false"):
        settings_for_profile(groq_model_include_reasoning=True)


def test_qwen_rollback_profile_has_a_compatible_parameter_set():
    settings = settings_for_profile(
        groq_model_profile="qwen3-32b-rollback",
        groq_model="qwen/qwen3-32b",
        groq_model_reasoning_effort="none",
        groq_model_response_format="json_object",
    )

    assert settings.groq_profile.supports_include_reasoning is False


def test_emergency_120b_profile_is_available_without_routing_creative_requests():
    settings = settings_for_profile(
        groq_model_profile="gpt-oss-120b-emergency",
        groq_model="openai/gpt-oss-120b",
    )

    assert settings.groq_profile.response_format == "json_schema"
