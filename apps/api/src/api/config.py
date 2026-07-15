import os
from dataclasses import dataclass
from typing import List

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class GroqModelProfile:
    model: str
    reasoning_efforts: frozenset[str]
    response_format: str
    supports_include_reasoning: bool


GROQ_MODEL_PROFILES = {
    "gpt-oss-20b": GroqModelProfile(
        model="openai/gpt-oss-20b",
        reasoning_efforts=frozenset({"low", "medium", "high"}),
        response_format="json_schema",
        supports_include_reasoning=True,
    ),
    # Production-safe whole-service rollback if the 20B canary must stop after Qwen retires.
    "gpt-oss-120b-emergency": GroqModelProfile(
        model="openai/gpt-oss-120b",
        reasoning_efforts=frozenset({"low", "medium", "high"}),
        response_format="json_schema",
        supports_include_reasoning=True,
    ),
    # Time-boxed rollback profile. Groq retires this model on 2026-07-17.
    "qwen3-32b-rollback": GroqModelProfile(
        model="qwen/qwen3-32b",
        reasoning_efforts=frozenset({"none", "default"}),
        response_format="json_object",
        supports_include_reasoning=False,
    ),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE", ".env"), extra="ignore")

    # API Settings
    api_host: str = "0.0.0.0"
    """IP address to bind the API server to"""
    api_port: int = 8000
    """Port to bind the API server to"""
    api_debug: bool = False
    """Enable API debug mode"""

    # Database Settings
    db_host: str = os.environ.get("DB_HOST") or os.environ.get("POSTGRES_HOST", "127.0.0.1")
    """Database host name or IP"""
    db_port: int = int(os.environ.get("DB_PORT") or os.environ.get("POSTGRES_PORT", "5432"))
    """Database port"""
    db_user: str = os.environ.get("DB_USER") or os.environ.get("POSTGRES_USER", "postgres")
    """Database username"""
    db_password: str = os.environ.get("DB_PASSWORD") or os.environ.get("POSTGRES_PASSWORD", "password")
    """Database password"""
    db_name: str = os.environ.get("DB_NAME") or os.environ.get("POSTGRES_DB", "domain_generator")
    """Database name"""
    db_driver: str = os.environ.get("DB_DRIVER", "asyncpg")
    """Database driver (asyncpg for PostgreSQL with TortoiseORM)"""

    # Redis Settings
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    """Redis connection URL for RQ usage"""
    rq_queue_name: str = os.environ.get("RQ_QUEUE", "domain_checks")
    """RQ queue name used for domain check jobs"""
    rq_job_timeout_seconds: int = int(os.environ.get("RQ_JOB_TIMEOUT_SECONDS", "30"))
    """How long the API waits for job results before returning UNKNOWN"""

    # Groq Settings
    groq_api_key: str | None = os.environ.get("GROQ_API_KEY")
    """Groq API key"""
    groq_model_profile: str = os.environ.get("GROQ_MODEL_PROFILE", "gpt-oss-20b")
    """Validated parameter profile for the selected Groq model"""
    groq_model: str = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    """Groq model to use"""
    groq_model_reasoning_effort: str = os.environ.get("GROQ_MODEL_REASONING_EFFORT", "low")
    """Groq model reasoning effort"""
    groq_model_stream: bool = os.environ.get("GROQ_MODEL_STREAM", False)
    """Must remain false because this client consumes complete responses"""
    groq_model_include_reasoning: bool = os.environ.get("GROQ_MODEL_INCLUDE_REASONING", False)
    """Must remain false because reasoning content is not consumed"""
    groq_model_response_format: str = os.environ.get("GROQ_MODEL_RESPONSE_FORMAT", "json_schema")
    """Response contract selected by the active model profile"""
    groq_model_temperature: float = os.environ.get("GROQ_MODEL_TEMPERATURE", 0.6)
    """Groq model temperature"""
    groq_model_max_completion_tokens: int = os.environ.get("GROQ_MODEL_MAX_COMPLETION_TOKENS", 4096)
    """Groq model max completion tokens"""
    groq_model_top_p: float = os.environ.get("GROQ_MODEL_TOP_P", 0.95)
    """Groq model top p"""
    groq_model_request_timeout_seconds: float = os.environ.get("GROQ_MODEL_REQUEST_TIMEOUT_SECONDS", 15.0)
    """Provider request timeout"""
    groq_validate_model_on_startup: bool = os.environ.get("GROQ_VALIDATE_MODEL_ON_STARTUP", True)
    """Verify that the configured model is available before accepting traffic"""
    groq_deployment_stage: str = os.environ.get("GROQ_DEPLOYMENT_STAGE", "production")
    """Deployment label exposed in model metrics"""

    # CORS Settings
    cors_allow_origins: str | None = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000")
    """Comma-separated list of allowed CORS origins"""

    # JWT Settings
    api_jwt_secret: str = os.environ.get("API_JWT_SECRET", "")
    """Shared secret used to validate API-bound JWTs"""
    api_jwt_algorithm: str = os.environ.get("API_JWT_ALGORITHM", "HS256")
    """JWT signing algorithm"""
    api_jwt_audience: str = os.environ.get("API_JWT_AUDIENCE", "domain-generator-api")
    """Expected JWT audience"""
    api_jwt_issuer: str = os.environ.get("API_JWT_ISSUER", "domain-generator-web")
    """Expected JWT issuer"""
    api_jwt_leeway_seconds: int = int(os.environ.get("API_JWT_LEEWAY_SECONDS", "10"))
    """Allowed leeway for exp/nbf validation"""

    # Suggestions Settings
    max_suggestions_retries: int = int(os.environ.get("MAX_SUGGESTIONS_RETRIES", "5"))
    """Maximum attempts to fetch enough available suggestions"""

    @model_validator(mode="after")
    def validate_groq_model_profile(self) -> "Settings":
        profile = GROQ_MODEL_PROFILES.get(self.groq_model_profile)
        if profile is None:
            supported = ", ".join(sorted(GROQ_MODEL_PROFILES))
            raise ValueError(f"Unknown GROQ_MODEL_PROFILE. Expected one of: {supported}")

        if self.groq_model != profile.model:
            raise ValueError(
                f"GROQ_MODEL_PROFILE={self.groq_model_profile} requires "
                f"GROQ_MODEL={profile.model}"
            )

        if self.groq_model_reasoning_effort not in profile.reasoning_efforts:
            allowed = ", ".join(sorted(profile.reasoning_efforts))
            raise ValueError(
                f"GROQ_MODEL_REASONING_EFFORT for {self.groq_model_profile} "
                f"must be one of: {allowed}"
            )

        if self.groq_model_response_format != profile.response_format:
            raise ValueError(
                f"GROQ_MODEL_PROFILE={self.groq_model_profile} requires "
                f"GROQ_MODEL_RESPONSE_FORMAT={profile.response_format}"
            )

        if self.groq_model_stream:
            raise ValueError("GROQ_MODEL_STREAM must be false; streaming completions are not consumed")

        if self.groq_model_include_reasoning:
            raise ValueError(
                "GROQ_MODEL_INCLUDE_REASONING must be false; reasoning content is not consumed"
            )

        if not 0 <= self.groq_model_temperature <= 2:
            raise ValueError("GROQ_MODEL_TEMPERATURE must be between 0 and 2")
        if not 0 <= self.groq_model_top_p <= 1:
            raise ValueError("GROQ_MODEL_TOP_P must be between 0 and 1")
        if self.groq_model_max_completion_tokens < 1:
            raise ValueError("GROQ_MODEL_MAX_COMPLETION_TOKENS must be positive")
        if self.groq_model_request_timeout_seconds <= 0:
            raise ValueError("GROQ_MODEL_REQUEST_TIMEOUT_SECONDS must be positive")
        return self

    @property
    def groq_profile(self) -> GroqModelProfile:
        return GROQ_MODEL_PROFILES[self.groq_model_profile]

    @computed_field(return_type=str)
    def database_url(self) -> str:
        """Return the database connection URL for TortoiseORM."""
        explicit_url = os.environ.get("DATABASE_URL")
        if explicit_url:
            return explicit_url

        # Format: postgres://user:password@host:port/database
        url = f"postgres://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return url
    
    def get_tortoise_config(self) -> dict:
        """Return TortoiseORM configuration dictionary."""
        return {
            "connections": {
                "default": self.database_url
            },
            "apps": {
                "models": {
                    "models": ["api.models.db_models", "aerich.models"],
                    "default_connection": "default",
                }
            },
        }

    @computed_field(return_type=List[str])
    def cors_allowed_origins(self) -> list[str]:
        """Return the parsed list of allowed CORS origins."""
        raw_value = self.cors_allow_origins or "http://localhost:3000"
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

_settings: Settings | None = None

def get_settings() -> Settings:
    """
    Get the settings object.

    :return: The settings object.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

TORTOISE_ORM = get_settings().get_tortoise_config()
