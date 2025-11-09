from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models import SystemConfig


@dataclass(slots=True)
class RuntimeConfig:
    chapter_interval_seconds: int
    evaluation_interval_chapters: int
    quality_score_min: float
    max_chapters_per_story: int
    min_active_stories: int
    max_active_stories: int
    context_window_chapters: int
    openai_model: str
    openai_premise_model: str
    openai_eval_model: str
    openai_temperature_chapter: float
    openai_temperature_premise: float
    openai_temperature_eval: float
    gpt5_reasoning_effort: str
    gpt5_verbosity: str

    def as_dict(self) -> dict[str, int | float | str]:
        return {
            "chapter_interval_seconds": self.chapter_interval_seconds,
            "evaluation_interval_chapters": self.evaluation_interval_chapters,
            "quality_score_min": self.quality_score_min,
            "max_chapters_per_story": self.max_chapters_per_story,
            "min_active_stories": self.min_active_stories,
            "max_active_stories": self.max_active_stories,
            "context_window_chapters": self.context_window_chapters,
            "openai_model": self.openai_model,
            "openai_premise_model": self.openai_premise_model,
            "openai_eval_model": self.openai_eval_model,
            "openai_temperature_chapter": self.openai_temperature_chapter,
            "openai_temperature_premise": self.openai_temperature_premise,
            "openai_temperature_eval": self.openai_temperature_eval,
            "gpt5_reasoning_effort": self.gpt5_reasoning_effort,
            "gpt5_verbosity": self.gpt5_verbosity,
        }


_settings = get_settings()

_CONFIG_SCHEMA: dict[str, dict[str, Any]] = {
    "chapter_interval_seconds": {"type": int, "min": 10, "max": 3600},
    "evaluation_interval_chapters": {"type": int, "min": 1, "max": 50},
    "quality_score_min": {"type": float, "min": 0.0, "max": 1.0},
    "max_chapters_per_story": {"type": int, "min": 1, "max": 500},
    "min_active_stories": {"type": int, "min": 0, "max": 100},
    "max_active_stories": {"type": int, "min": 1, "max": 200},
    "context_window_chapters": {"type": int, "min": 1, "max": 50},
    "openai_model": {"type": str, "min_length": 1, "max_length": 128},
    "openai_premise_model": {"type": str, "min_length": 1, "max_length": 128},
    "openai_eval_model": {"type": str, "min_length": 1, "max_length": 128},
    "openai_temperature_chapter": {"type": float, "min": 0.0, "max": 2.0},
    "openai_temperature_premise": {"type": float, "min": 0.0, "max": 2.0},
    "openai_temperature_eval": {"type": float, "min": 0.0, "max": 2.0},
    "gpt5_reasoning_effort": {
        "type": str,
        "choices": ["minimal", "low", "medium", "high"],
    },
    "gpt5_verbosity": {
        "type": str,
        "choices": ["low", "medium", "high"],
    },
}

_DEFAULTS: dict[str, int | float | str] = {
    key: getattr(_settings, key)
    for key in _CONFIG_SCHEMA
}


def _coerce_value(key: str, value: Any) -> int | float | str:
    meta = _CONFIG_SCHEMA[key]
    target = meta["type"]
    if value is None:
        return _DEFAULTS[key]
    if target is int:
        if isinstance(value, (int, float)):
            coerced = int(value)
        elif isinstance(value, str) and value.strip():
            coerced = int(float(value))
        else:
            raise ValueError(f"Invalid value for {key}")
    elif target is float:
        if isinstance(value, (int, float)):
            coerced = float(value)
        elif isinstance(value, str) and value.strip():
            coerced = float(value)
        else:
            raise ValueError(f"Invalid value for {key}")
    elif target is str:
        if isinstance(value, str):
            coerced = value.strip()
        else:
            coerced = str(value).strip()
        if not coerced:
            raise ValueError(f"{key} cannot be empty")
        min_length = meta.get("min_length")
        max_length = meta.get("max_length")
        if min_length is not None and len(coerced) < min_length:
            raise ValueError(f"{key} must be at least {min_length} characters")
        if max_length is not None and len(coerced) > max_length:
            raise ValueError(f"{key} must be at most {max_length} characters")
        choices = meta.get("choices")
        if choices is not None and coerced not in choices:
            raise ValueError(
                f"{key} must be one of {', '.join(choices)}"
            )
        return coerced
    else:
        raise ValueError(f"Unsupported type for {key}")

    minimum = meta.get("min")
    maximum = meta.get("max")
    if minimum is not None and coerced < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    if maximum is not None and coerced > maximum:
        raise ValueError(f"{key} must be <= {maximum}")
    return coerced if target is float else int(coerced)


def _validate_updates(
    updates: Mapping[str, Any], current: RuntimeConfig
) -> dict[str, int | float | str]:
    if not updates:
        return {}
    cleaned: dict[str, int | float | str] = {}
    for key, value in updates.items():
        if key not in _CONFIG_SCHEMA:
            raise ValueError(f"Unknown configuration key: {key}")
        cleaned[key] = _coerce_value(key, value)

    min_active = cleaned.get("min_active_stories", current.min_active_stories)
    max_active = cleaned.get("max_active_stories", current.max_active_stories)
    if min_active > max_active:
        raise ValueError("min_active_stories cannot exceed max_active_stories")

    return cleaned


async def get_runtime_config(session: AsyncSession) -> RuntimeConfig:
    stmt = select(SystemConfig.key, SystemConfig.value)
    records = (await session.execute(stmt)).all()
    stored: dict[str, Any] = {key: value for key, value in records}

    values = {
        key: _coerce_value(key, stored.get(key, _DEFAULTS[key]))
        for key in _CONFIG_SCHEMA
    }

    return RuntimeConfig(**values)


async def apply_config_updates(
    session: AsyncSession, updates: Mapping[str, Any]
) -> RuntimeConfig:
    current = await get_runtime_config(session)
    cleaned = _validate_updates(updates, current)
    if not cleaned:
        return current

    for key, value in cleaned.items():
        row = await session.get(SystemConfig, key)
        if row is None:
            row = SystemConfig(key=key, value=value)
            session.add(row)
        else:
            row.value = value

    await session.flush()
    return await get_runtime_config(session)


__all__ = ["RuntimeConfig", "get_runtime_config", "apply_config_updates"]
