from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_file_encoding="utf-8")

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
    enable_websocket: bool = Field(True, alias="ENABLE_WEBSOCKET")

    public_api_url: Annotated[str | None, Field(default=None, alias="PUBLIC_API_URL")]

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
