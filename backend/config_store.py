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

    def as_dict(self) -> dict[str, int | float]:
        return {
            "chapter_interval_seconds": self.chapter_interval_seconds,
            "evaluation_interval_chapters": self.evaluation_interval_chapters,
            "quality_score_min": self.quality_score_min,
            "max_chapters_per_story": self.max_chapters_per_story,
            "min_active_stories": self.min_active_stories,
            "max_active_stories": self.max_active_stories,
            "context_window_chapters": self.context_window_chapters,
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
}

_DEFAULTS: dict[str, int | float] = {
    key: getattr(_settings, key)
    for key in _CONFIG_SCHEMA
}


def _coerce_value(key: str, value: Any) -> int | float:
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
    else:
        if isinstance(value, (int, float)):
            coerced = float(value)
        elif isinstance(value, str) and value.strip():
            coerced = float(value)
        else:
            raise ValueError(f"Invalid value for {key}")

    minimum = meta.get("min")
    maximum = meta.get("max")
    if minimum is not None and coerced < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    if maximum is not None and coerced > maximum:
        raise ValueError(f"{key} must be <= {maximum}")
    return coerced if target is float else int(coerced)


def _validate_updates(
    updates: Mapping[str, Any], current: RuntimeConfig
) -> dict[str, int | float]:
    if not updates:
        return {}
    cleaned: dict[str, int | float] = {}
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
