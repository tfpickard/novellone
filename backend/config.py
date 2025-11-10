from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="allow", env_file_encoding="utf-8"
    )

    database_url: str = Field(..., alias="DATABASE_URL")

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(..., alias="OPENAI_MODEL")
    openai_premise_model: str = Field(..., alias="OPENAI_PREMISE_MODEL")
    openai_eval_model: str = Field(..., alias="OPENAI_EVAL_MODEL")
    openai_max_tokens_chapter: int = Field(..., alias="OPENAI_MAX_TOKENS_CHAPTER")
    openai_max_tokens_premise: int = Field(..., alias="OPENAI_MAX_TOKENS_PREMISE")
    openai_max_tokens_eval: int = Field(..., alias="OPENAI_MAX_TOKENS_EVAL")
    openai_temperature_chapter: float = Field(..., alias="OPENAI_TEMPERATURE_CHAPTER")
    openai_temperature_premise: float = Field(..., alias="OPENAI_TEMPERATURE_PREMISE")
    openai_temperature_eval: float = Field(..., alias="OPENAI_TEMPERATURE_EVAL")

    premise_prompt_refresh_interval: int = Field(
        ..., alias="PREMISE_PROMPT_REFRESH_INTERVAL"
    )
    premise_prompt_stats_window: int = Field(
        ..., alias="PREMISE_PROMPT_STATS_WINDOW"
    )
    premise_prompt_variation_strength: float = Field(
        ..., alias="PREMISE_PROMPT_VARIATION_STRENGTH"
    )
    chaos_initial_min: float = Field(0.05, alias="CHAOS_INITIAL_MIN")
    chaos_initial_max: float = Field(0.25, alias="CHAOS_INITIAL_MAX")
    chaos_increment_min: float = Field(0.02, alias="CHAOS_INCREMENT_MIN")
    chaos_increment_max: float = Field(0.15, alias="CHAOS_INCREMENT_MAX")

    chapter_interval_seconds: int = Field(..., alias="CHAPTER_INTERVAL_SECONDS")
    evaluation_interval_chapters: int = Field(..., alias="EVALUATION_INTERVAL_CHAPTERS")
    worker_tick_interval: int = Field(..., alias="WORKER_TICK_INTERVAL")

    min_active_stories: int = Field(..., alias="MIN_ACTIVE_STORIES")
    max_active_stories: int = Field(..., alias="MAX_ACTIVE_STORIES")
    context_window_chapters: int = Field(..., alias="CONTEXT_WINDOW_CHAPTERS")
    max_chapters_per_story: int = Field(..., alias="MAX_CHAPTERS_PER_STORY")
    min_chapters_before_eval: int = Field(..., alias="MIN_CHAPTERS_BEFORE_EVAL")

    quality_score_min: float = Field(..., alias="QUALITY_SCORE_MIN")
    coherence_weight: float = Field(..., alias="COHERENCE_WEIGHT")
    novelty_weight: float = Field(..., alias="NOVELTY_WEIGHT")
    engagement_weight: float = Field(..., alias="ENGAGEMENT_WEIGHT")
    pacing_weight: float = Field(..., alias="PACING_WEIGHT")

    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = Field(
        "INFO", alias="LOG_LEVEL"
    )
    log_dir: str = Field("/app/logs", alias="LOG_DIR")
    log_max_bytes: int = Field(5_000_000, alias="LOG_MAX_BYTES")
    log_backup_count: int = Field(5, alias="LOG_BACKUP_COUNT")
    enable_websocket: bool = Field(True, alias="ENABLE_WEBSOCKET")

    public_api_url: Annotated[str | None, Field(default=None, alias="PUBLIC_API_URL")]

    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="stupishly", alias="ADMIN_PASSWORD")
    admin_password_hash: str = Field(default="", alias="ADMIN_PASSWORD_HASH")
    session_secret: str = Field("stupishly", alias="SESSION_SECRET")
    session_ttl_seconds: int = Field(7 * 24 * 3600, alias="SESSION_TTL_SECONDS")
    session_cookie_name: str = Field("novellone_session", alias="SESSION_COOKIE_NAME")
    session_cookie_domain: Annotated[
        str | None, Field(default=None, alias="SESSION_COOKIE_DOMAIN")
    ]
    session_cookie_secure: bool = Field(False, alias="SESSION_COOKIE_SECURE")
    session_cookie_samesite: Literal["lax", "strict", "none"] = Field(
        "lax", alias="SESSION_COOKIE_SAMESITE"
    )

    @field_validator("admin_password_hash", mode="after")
    @classmethod
    def hash_admin_password(cls, v: str, info) -> str:
        import sys
        print(f"[DEBUG] hash_admin_password validator called", file=sys.stderr)
        print(f"[DEBUG]   admin_password_hash value: {v!r}", file=sys.stderr)
        print(f"[DEBUG]   admin_password from info.data: {info.data.get('admin_password', '')!r}", file=sys.stderr)
        
        # If hash is already provided, use it
        if v:
            print(f"[DEBUG]   Using existing hash", file=sys.stderr)
            return v
        
        # Otherwise hash the cleartext password
        password = info.data.get("admin_password", "")
        if not password:
            print(f"[DEBUG]   ERROR: Both password and hash are empty!", file=sys.stderr)
            raise ValueError("Either ADMIN_PASSWORD or ADMIN_PASSWORD_HASH must be set")
        
        print(f"[DEBUG]   Hashing cleartext password (length: {len(password)})", file=sys.stderr)
        
        # Truncate to 72 bytes if needed (bcrypt limitation)
        if len(password.encode("utf-8")) > 72:
            password = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
            print(f"[DEBUG]   Truncated password to 72 bytes", file=sys.stderr)
        
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_context.hash(password)
        print(f"[DEBUG]   Generated hash: {hashed[:20]}...", file=sys.stderr)
        return hashed

    @property
    def evaluation_weights(self) -> "EvaluationWeights":
        return EvaluationWeights(
            coherence=self.coherence_weight,
            novelty=self.novelty_weight,
            engagement=self.engagement_weight,
            pacing=self.pacing_weight,
        )


class EvaluationWeights(BaseModel):
    coherence: float
    novelty: float
    engagement: float
    pacing: float

    @property
    def total(self) -> float:
        return self.coherence + self.novelty + self.engagement + self.pacing


@lru_cache
def get_settings() -> AppSettings:
    settings = AppSettings()
    total_weight = settings.evaluation_weights.total
    if not abs(total_weight - 1.0) < 1e-6:
        raise ValueError(
            "Evaluation weights must sum to 1.0. Currently: %.3f" % total_weight
        )
    return settings


__all__ = ["AppSettings", "get_settings"]
