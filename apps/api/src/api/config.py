import os

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE", ".env"), extra="ignore")

    api_host: str = "0.0.0.0"
    """IP address to bind the API server to"""
    api_port: int = 8000
    """Port to bind the API server to"""
    api_debug: bool = False
    """Enable API debug mode"""

    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    """Redis connection URL for RQ usage"""

    rq_queue_name: str = os.environ.get("RQ_QUEUE", "domain_checks")
    """RQ queue name used for domain check jobs"""

    rq_job_timeout_seconds: int = int(os.environ.get("RQ_JOB_TIMEOUT_SECONDS", "30"))
    """How long the API waits for job results before returning UNKNOWN"""

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