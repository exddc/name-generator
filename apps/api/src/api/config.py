import os

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    groq_api_key: str = os.environ.get("GROQ_API_KEY")
    """Groq API key"""
    groq_model: str = os.environ.get("GROQ_MODEL", "qwen/qwen3-32b")
    """Groq model to use"""
    groq_model_reasoning_effort: str = os.environ.get("GROQ_MODEL_REASONING_EFFORT", "none")
    """Groq model reasoning effort"""
    groq_model_stream: bool = os.environ.get("GROQ_MODEL_STREAM", False)
    """Groq model stream"""
    groq_model_temperature: float = os.environ.get("GROQ_MODEL_TEMPERATURE", 0.6)
    """Groq model temperature"""
    groq_model_max_completion_tokens: int = os.environ.get("GROQ_MODEL_MAX_COMPLETION_TOKENS", 4096)
    """Groq model max completion tokens"""
    groq_model_top_p: float = os.environ.get("GROQ_MODEL_TOP_P", 0.95)
    """Groq model top p"""

    # Suggestions Settings
    max_suggestions_retries: int = int(os.environ.get("MAX_SUGGESTIONS_RETRIES", "5"))
    """Maximum attempts to fetch enough available suggestions"""

    @computed_field(return_type=str)
    def database_url(self) -> str:
        """Return the database connection URL for TortoiseORM."""
        explicit_url = os.environ.get("DATABASE_URL")
        if explicit_url:
            return explicit_url

        # Format: postgres://user:password@host:port/database
        url = f"postgres://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        print(f"Database URL: {url}")
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

# Aerich configuration - accessed during migration generation
TORTOISE_ORM = get_settings().get_tortoise_config()