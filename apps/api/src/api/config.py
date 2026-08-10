import os
from dataclasses import dataclass
from typing import List

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


SUPPORTED_GROQ_REASONING_EFFORTS = frozenset({"low", "medium", "high"})


@dataclass(frozen=True)
class GroqModelProfile:
    """Immutable provider parameters selected for one generation request."""

    name: str
    model: str
    reasoning_effort: str
    temperature: float
    max_completion_tokens: int
    top_p: float
    input_cost_per_million: float
    cached_input_cost_per_million: float
    output_cost_per_million: float

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
    groq_model: str = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    """Groq model to use"""
    groq_model_reasoning_effort: str = os.environ.get("GROQ_MODEL_REASONING_EFFORT", "low")
    """Groq model reasoning effort"""
    groq_model_stream: bool = os.environ.get("GROQ_MODEL_STREAM", False)
    """Must remain false because this client consumes complete responses"""
    groq_model_temperature: float = os.environ.get("GROQ_MODEL_TEMPERATURE", 0.6)
    """Groq model temperature"""
    groq_model_max_completion_tokens: int = os.environ.get("GROQ_MODEL_MAX_COMPLETION_TOKENS", 4096)
    """Groq model max completion tokens"""
    groq_model_top_p: float = os.environ.get("GROQ_MODEL_TOP_P", 0.95)
    """Groq model top p"""
    groq_model_input_cost_per_million: float = os.environ.get(
        "GROQ_MODEL_INPUT_COST_PER_MILLION", 0.075
    )
    """GPT-OSS 20B input price in USD per million tokens"""
    groq_model_cached_input_cost_per_million: float = os.environ.get(
        "GROQ_MODEL_CACHED_INPUT_COST_PER_MILLION", 0.0375
    )
    """GPT-OSS 20B cached-input price in USD per million tokens"""
    groq_model_output_cost_per_million: float = os.environ.get(
        "GROQ_MODEL_OUTPUT_COST_PER_MILLION", 0.30
    )
    """GPT-OSS 20B output price in USD per million tokens"""

    # The creative profile is intentionally configured independently from the default
    # profile so request routing never mutates shared settings.
    groq_creative_model: str = os.environ.get(
        "GROQ_CREATIVE_MODEL", "openai/gpt-oss-120b"
    )
    """Groq model used only for PromptType.LEXICON requests"""
    groq_creative_model_reasoning_effort: str = os.environ.get(
        "GROQ_CREATIVE_MODEL_REASONING_EFFORT", "low"
    )
    """GPT-OSS 120B reasoning effort"""
    groq_creative_model_stream: bool = os.environ.get(
        "GROQ_CREATIVE_MODEL_STREAM", False
    )
    """Must remain false because strict structured outputs do not support streaming"""
    groq_creative_model_temperature: float = os.environ.get(
        "GROQ_CREATIVE_MODEL_TEMPERATURE", 0.6
    )
    groq_creative_model_max_completion_tokens: int = os.environ.get(
        "GROQ_CREATIVE_MODEL_MAX_COMPLETION_TOKENS", 4096
    )
    groq_creative_model_top_p: float = os.environ.get(
        "GROQ_CREATIVE_MODEL_TOP_P", 0.95
    )
    groq_creative_model_input_cost_per_million: float = os.environ.get(
        "GROQ_CREATIVE_MODEL_INPUT_COST_PER_MILLION", 0.15
    )
    groq_creative_model_cached_input_cost_per_million: float = os.environ.get(
        "GROQ_CREATIVE_MODEL_CACHED_INPUT_COST_PER_MILLION", 0.075
    )
    groq_creative_model_output_cost_per_million: float = os.environ.get(
        "GROQ_CREATIVE_MODEL_OUTPUT_COST_PER_MILLION", 0.60
    )
    groq_creative_fallback_to_default: bool = os.environ.get(
        "GROQ_CREATIVE_FALLBACK_TO_DEFAULT", False
    )
    """Opt-in 20B fallback for transient 120B provider failures; disabled by default"""
    groq_creative_revalidation_seconds: float = os.environ.get(
        "GROQ_CREATIVE_REVALIDATION_SECONDS", 30.0
    )
    """Seconds before one request probes an unavailable creative model again"""
    groq_model_request_timeout_seconds: float = os.environ.get("GROQ_MODEL_REQUEST_TIMEOUT_SECONDS", 15.0)
    """Provider request timeout"""
    groq_validate_model_on_startup: bool = os.environ.get("GROQ_VALIDATE_MODEL_ON_STARTUP", True)
    """Verify that the configured model is available before accepting traffic"""

    # Monitoring
    monitoring_canary_token: str = os.environ.get("MONITORING_CANARY_TOKEN", "")
    """Shared secret for /health/canary probes from the external monitor"""

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
    """Maximum model-call attempts per generation request (worst-case LLM fan-out)."""

    # Burst window (short) for anonymous/authenticated abuse spikes.
    generation_quota_burst_window_seconds: int = int(
        os.environ.get(
            "GENERATION_QUOTA_BURST_WINDOW_SECONDS",
            os.environ.get("GENERATION_QUOTA_WINDOW_SECONDS", "60"),
        )
    )
    generation_quota_anonymous_burst: int = int(
        os.environ.get(
            "GENERATION_QUOTA_ANONYMOUS_BURST",
            os.environ.get("GENERATION_QUOTA_ANONYMOUS", "5"),
        )
    )
    generation_quota_authenticated_burst: int = int(
        os.environ.get(
            "GENERATION_QUOTA_AUTHENTICATED_BURST",
            os.environ.get("GENERATION_QUOTA_AUTHENTICATED", "50"),
        )
    )
    generation_quota_anonymous_network_burst: int = int(
        os.environ.get(
            "GENERATION_QUOTA_ANONYMOUS_NETWORK_BURST",
            os.environ.get("GENERATION_QUOTA_ANONYMOUS_NETWORK", "20"),
        )
    )

    # Daily window for sustained cost bounds.
    generation_quota_daily_window_seconds: int = int(
        os.environ.get("GENERATION_QUOTA_DAILY_WINDOW_SECONDS", "86400")
    )
    generation_quota_anonymous_daily: int = int(
        os.environ.get("GENERATION_QUOTA_ANONYMOUS_DAILY", "20")
    )
    generation_quota_authenticated_daily: int = int(
        os.environ.get("GENERATION_QUOTA_AUTHENTICATED_DAILY", "200")
    )
    generation_quota_anonymous_network_daily: int = int(
        os.environ.get("GENERATION_QUOTA_ANONYMOUS_NETWORK_DAILY", "100")
    )

    # Cumulative resource budgets (burst + daily) charged across generation,
    # similar, and variants paths.
    candidates_quota_anonymous_burst: int = int(
        os.environ.get("CANDIDATES_QUOTA_ANONYMOUS_BURST", "100")
    )
    candidates_quota_authenticated_burst: int = int(
        os.environ.get("CANDIDATES_QUOTA_AUTHENTICATED_BURST", "400")
    )
    candidates_quota_anonymous_daily: int = int(
        os.environ.get("CANDIDATES_QUOTA_ANONYMOUS_DAILY", "400")
    )
    candidates_quota_authenticated_daily: int = int(
        os.environ.get("CANDIDATES_QUOTA_AUTHENTICATED_DAILY", "4000")
    )
    tokens_quota_anonymous_burst: int = int(
        os.environ.get("TOKENS_QUOTA_ANONYMOUS_BURST", "50000")
    )
    tokens_quota_authenticated_burst: int = int(
        os.environ.get("TOKENS_QUOTA_AUTHENTICATED_BURST", "200000")
    )
    tokens_quota_anonymous_daily: int = int(
        os.environ.get("TOKENS_QUOTA_ANONYMOUS_DAILY", "200000")
    )
    tokens_quota_authenticated_daily: int = int(
        os.environ.get("TOKENS_QUOTA_AUTHENTICATED_DAILY", "2000000")
    )
    checker_jobs_quota_anonymous_burst: int = int(
        os.environ.get("CHECKER_JOBS_QUOTA_ANONYMOUS_BURST", "100")
    )
    checker_jobs_quota_authenticated_burst: int = int(
        os.environ.get("CHECKER_JOBS_QUOTA_AUTHENTICATED_BURST", "400")
    )
    checker_jobs_quota_anonymous_daily: int = int(
        os.environ.get("CHECKER_JOBS_QUOTA_ANONYMOUS_DAILY", "400")
    )
    checker_jobs_quota_authenticated_daily: int = int(
        os.environ.get("CHECKER_JOBS_QUOTA_AUTHENTICATED_DAILY", "4000")
    )

    # Concurrency and wall-clock budgets per identity.
    concurrent_generations_anonymous: int = int(
        os.environ.get("CONCURRENT_GENERATIONS_ANONYMOUS", "1")
    )
    concurrent_generations_authenticated: int = int(
        os.environ.get("CONCURRENT_GENERATIONS_AUTHENTICATED", "3")
    )
    request_wall_time_seconds: float = float(
        os.environ.get("REQUEST_WALL_TIME_SECONDS", "60")
    )
    max_candidates_per_request: int = int(
        os.environ.get("MAX_CANDIDATES_PER_REQUEST", "100")
    )
    max_checker_jobs_per_request: int = int(
        os.environ.get("MAX_CHECKER_JOBS_PER_REQUEST", "100")
    )
    max_tokens_per_request: int = int(
        os.environ.get("MAX_TOKENS_PER_REQUEST", "50000")
    )

    # Global queue backpressure (stable 503 instead of unbounded growth).
    rq_max_queue_depth: int = int(os.environ.get("RQ_MAX_QUEUE_DEPTH", "500"))
    rq_max_queue_age_seconds: float = float(
        os.environ.get("RQ_MAX_QUEUE_AGE_SECONDS", "60")
    )
    queue_saturation_retry_after_seconds: int = int(
        os.environ.get("QUEUE_SATURATION_RETRY_AFTER_SECONDS", "15")
    )

    # Emergency kill switch for generation endpoints.
    emergency_circuit_breaker: bool = os.environ.get(
        "EMERGENCY_CIRCUIT_BREAKER", "false"
    ).lower() in {"1", "true", "yes", "on"}
    circuit_breaker_retry_after_seconds: int = int(
        os.environ.get("CIRCUIT_BREAKER_RETRY_AFTER_SECONDS", "60")
    )

    # Idempotency for duplicate client retries.
    idempotency_ttl_seconds: int = int(
        os.environ.get("IDEMPOTENCY_TTL_SECONDS", "86400")
    )

    # Legacy aliases used by older env files / tests (mapped to burst).
    generation_quota_window_seconds: int = int(
        os.environ.get(
            "GENERATION_QUOTA_WINDOW_SECONDS",
            os.environ.get("GENERATION_QUOTA_BURST_WINDOW_SECONDS", "60"),
        )
    )
    generation_quota_anonymous: int = int(
        os.environ.get(
            "GENERATION_QUOTA_ANONYMOUS",
            os.environ.get("GENERATION_QUOTA_ANONYMOUS_BURST", "5"),
        )
    )
    generation_quota_authenticated: int = int(
        os.environ.get(
            "GENERATION_QUOTA_AUTHENTICATED",
            os.environ.get("GENERATION_QUOTA_AUTHENTICATED_BURST", "50"),
        )
    )
    generation_quota_anonymous_network: int = int(
        os.environ.get(
            "GENERATION_QUOTA_ANONYMOUS_NETWORK",
            os.environ.get("GENERATION_QUOTA_ANONYMOUS_NETWORK_BURST", "20"),
        )
    )
    redis_connect_timeout_seconds: float = float(
        os.environ.get("REDIS_CONNECT_TIMEOUT_SECONDS", "0.5")
    )
    redis_socket_timeout_seconds: float = float(
        os.environ.get("REDIS_SOCKET_TIMEOUT_SECONDS", "1.0")
    )

    @model_validator(mode="after")
    def validate_groq_model_config(self) -> "Settings":
        if self.groq_model != "openai/gpt-oss-20b":
            raise ValueError("GROQ_MODEL must be openai/gpt-oss-20b")

        if self.groq_model_reasoning_effort not in SUPPORTED_GROQ_REASONING_EFFORTS:
            raise ValueError(
                "GROQ_MODEL_REASONING_EFFORT must be one of: high, low, medium"
            )

        if self.groq_model_stream:
            raise ValueError("GROQ_MODEL_STREAM must be false; streaming completions are not consumed")

        if self.groq_creative_model != "openai/gpt-oss-120b":
            raise ValueError("GROQ_CREATIVE_MODEL must be openai/gpt-oss-120b")
        if self.groq_creative_model_reasoning_effort not in SUPPORTED_GROQ_REASONING_EFFORTS:
            raise ValueError(
                "GROQ_CREATIVE_MODEL_REASONING_EFFORT must be one of: high, low, medium"
            )
        if self.groq_creative_model_stream:
            raise ValueError(
                "GROQ_CREATIVE_MODEL_STREAM must be false; strict JSON Schema does not support streaming"
            )

        if not 0 <= self.groq_model_temperature <= 2:
            raise ValueError("GROQ_MODEL_TEMPERATURE must be between 0 and 2")
        if not 0 <= self.groq_model_top_p <= 1:
            raise ValueError("GROQ_MODEL_TOP_P must be between 0 and 1")
        if not 0 <= self.groq_creative_model_temperature <= 2:
            raise ValueError("GROQ_CREATIVE_MODEL_TEMPERATURE must be between 0 and 2")
        if not 0 <= self.groq_creative_model_top_p <= 1:
            raise ValueError("GROQ_CREATIVE_MODEL_TOP_P must be between 0 and 1")
        if self.groq_model_max_completion_tokens < 1:
            raise ValueError("GROQ_MODEL_MAX_COMPLETION_TOKENS must be positive")
        if self.groq_creative_model_max_completion_tokens < 1:
            raise ValueError("GROQ_CREATIVE_MODEL_MAX_COMPLETION_TOKENS must be positive")
        if self.groq_model_request_timeout_seconds <= 0:
            raise ValueError("GROQ_MODEL_REQUEST_TIMEOUT_SECONDS must be positive")
        if self.groq_creative_revalidation_seconds < 0:
            raise ValueError("GROQ_CREATIVE_REVALIDATION_SECONDS must not be negative")
        positive_ints = {
            "GENERATION_QUOTA_BURST_WINDOW_SECONDS": self.generation_quota_burst_window_seconds,
            "GENERATION_QUOTA_DAILY_WINDOW_SECONDS": self.generation_quota_daily_window_seconds,
            "GENERATION_QUOTA_ANONYMOUS_BURST": self.generation_quota_anonymous_burst,
            "GENERATION_QUOTA_AUTHENTICATED_BURST": self.generation_quota_authenticated_burst,
            "GENERATION_QUOTA_ANONYMOUS_NETWORK_BURST": self.generation_quota_anonymous_network_burst,
            "GENERATION_QUOTA_ANONYMOUS_DAILY": self.generation_quota_anonymous_daily,
            "GENERATION_QUOTA_AUTHENTICATED_DAILY": self.generation_quota_authenticated_daily,
            "GENERATION_QUOTA_ANONYMOUS_NETWORK_DAILY": self.generation_quota_anonymous_network_daily,
            "CANDIDATES_QUOTA_ANONYMOUS_BURST": self.candidates_quota_anonymous_burst,
            "CANDIDATES_QUOTA_AUTHENTICATED_BURST": self.candidates_quota_authenticated_burst,
            "CANDIDATES_QUOTA_ANONYMOUS_DAILY": self.candidates_quota_anonymous_daily,
            "CANDIDATES_QUOTA_AUTHENTICATED_DAILY": self.candidates_quota_authenticated_daily,
            "TOKENS_QUOTA_ANONYMOUS_BURST": self.tokens_quota_anonymous_burst,
            "TOKENS_QUOTA_AUTHENTICATED_BURST": self.tokens_quota_authenticated_burst,
            "TOKENS_QUOTA_ANONYMOUS_DAILY": self.tokens_quota_anonymous_daily,
            "TOKENS_QUOTA_AUTHENTICATED_DAILY": self.tokens_quota_authenticated_daily,
            "CHECKER_JOBS_QUOTA_ANONYMOUS_BURST": self.checker_jobs_quota_anonymous_burst,
            "CHECKER_JOBS_QUOTA_AUTHENTICATED_BURST": self.checker_jobs_quota_authenticated_burst,
            "CHECKER_JOBS_QUOTA_ANONYMOUS_DAILY": self.checker_jobs_quota_anonymous_daily,
            "CHECKER_JOBS_QUOTA_AUTHENTICATED_DAILY": self.checker_jobs_quota_authenticated_daily,
            "CONCURRENT_GENERATIONS_ANONYMOUS": self.concurrent_generations_anonymous,
            "CONCURRENT_GENERATIONS_AUTHENTICATED": self.concurrent_generations_authenticated,
            "MAX_CANDIDATES_PER_REQUEST": self.max_candidates_per_request,
            "MAX_CHECKER_JOBS_PER_REQUEST": self.max_checker_jobs_per_request,
            "MAX_TOKENS_PER_REQUEST": self.max_tokens_per_request,
            "RQ_MAX_QUEUE_DEPTH": self.rq_max_queue_depth,
            "QUEUE_SATURATION_RETRY_AFTER_SECONDS": self.queue_saturation_retry_after_seconds,
            "CIRCUIT_BREAKER_RETRY_AFTER_SECONDS": self.circuit_breaker_retry_after_seconds,
            "IDEMPOTENCY_TTL_SECONDS": self.idempotency_ttl_seconds,
            "GENERATION_QUOTA_WINDOW_SECONDS": self.generation_quota_window_seconds,
            "GENERATION_QUOTA_ANONYMOUS": self.generation_quota_anonymous,
            "GENERATION_QUOTA_AUTHENTICATED": self.generation_quota_authenticated,
            "GENERATION_QUOTA_ANONYMOUS_NETWORK": self.generation_quota_anonymous_network,
            "MAX_SUGGESTIONS_RETRIES": self.max_suggestions_retries,
        }
        for name, value in positive_ints.items():
            if value < 1:
                raise ValueError(f"{name} must be positive")
        if self.request_wall_time_seconds <= 0:
            raise ValueError("REQUEST_WALL_TIME_SECONDS must be positive")
        if self.rq_max_queue_age_seconds <= 0:
            raise ValueError("RQ_MAX_QUEUE_AGE_SECONDS must be positive")
        if self.redis_connect_timeout_seconds <= 0:
            raise ValueError("REDIS_CONNECT_TIMEOUT_SECONDS must be positive")
        if self.redis_socket_timeout_seconds <= 0:
            raise ValueError("REDIS_SOCKET_TIMEOUT_SECONDS must be positive")
        cost_fields = {
            "GROQ_MODEL_INPUT_COST_PER_MILLION": self.groq_model_input_cost_per_million,
            "GROQ_MODEL_CACHED_INPUT_COST_PER_MILLION": self.groq_model_cached_input_cost_per_million,
            "GROQ_MODEL_OUTPUT_COST_PER_MILLION": self.groq_model_output_cost_per_million,
            "GROQ_CREATIVE_MODEL_INPUT_COST_PER_MILLION": self.groq_creative_model_input_cost_per_million,
            "GROQ_CREATIVE_MODEL_CACHED_INPUT_COST_PER_MILLION": self.groq_creative_model_cached_input_cost_per_million,
            "GROQ_CREATIVE_MODEL_OUTPUT_COST_PER_MILLION": self.groq_creative_model_output_cost_per_million,
        }
        for name, value in cost_fields.items():
            if value < 0:
                raise ValueError(f"{name} must not be negative")
        return self

    @property
    def groq_default_profile(self) -> GroqModelProfile:
        return GroqModelProfile(
            name="default",
            model=self.groq_model,
            reasoning_effort=self.groq_model_reasoning_effort,
            temperature=self.groq_model_temperature,
            max_completion_tokens=self.groq_model_max_completion_tokens,
            top_p=self.groq_model_top_p,
            input_cost_per_million=self.groq_model_input_cost_per_million,
            cached_input_cost_per_million=self.groq_model_cached_input_cost_per_million,
            output_cost_per_million=self.groq_model_output_cost_per_million,
        )

    @property
    def groq_creative_profile(self) -> GroqModelProfile:
        return GroqModelProfile(
            name="creative",
            model=self.groq_creative_model,
            reasoning_effort=self.groq_creative_model_reasoning_effort,
            temperature=self.groq_creative_model_temperature,
            max_completion_tokens=self.groq_creative_model_max_completion_tokens,
            top_p=self.groq_creative_model_top_p,
            input_cost_per_million=self.groq_creative_model_input_cost_per_million,
            cached_input_cost_per_million=self.groq_creative_model_cached_input_cost_per_million,
            output_cost_per_million=self.groq_creative_model_output_cost_per_million,
        )

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
