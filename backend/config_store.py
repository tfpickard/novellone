from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models import SystemConfig


@dataclass(slots=True)
class ContentAxisSettings:
    average_level: float
    momentum: float
    premise_multiplier: float

    def as_dict(self) -> dict[str, float]:
        return {
            "average_level": self.average_level,
            "momentum": self.momentum,
            "premise_multiplier": self.premise_multiplier,
        }


CONTENT_AXIS_KEYS: tuple[str, ...] = (
    "sexual_content",
    "violence",
    "strong_language",
    "drug_use",
    "horror_suspense",
    "gore_graphic_imagery",
    "romance_focus",
    "crime_illicit_activity",
    "political_ideology",
    "supernatural_occult",
)


_CONTENT_AXIS_KEY_SET = set(CONTENT_AXIS_KEYS)


_DEFAULT_CONTENT_AXES: dict[str, dict[str, float]] = {
    axis: {"average_level": 2.0, "momentum": 0.0, "premise_multiplier": 1.0}
    for axis in CONTENT_AXIS_KEYS
}


def _content_axis_defaults() -> dict[str, dict[str, float]]:
    return {axis: values.copy() for axis, values in _DEFAULT_CONTENT_AXES.items()}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _get_numeric(value: Any, default: float, label: str) -> float:
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return float(default)
        try:
            return float(stripped)
        except ValueError as exc:  # noqa: B904
            raise ValueError(f"{label} must be a number") from exc
    raise ValueError(f"{label} must be a number")


def _sanitize_axis_payload(axis_key: str, payload: Mapping[str, Any]) -> dict[str, float]:
    defaults = _DEFAULT_CONTENT_AXES[axis_key]
    average_level = _clamp(
        _get_numeric(
            payload.get("average_level"),
            defaults["average_level"],
            f"{axis_key}.average_level",
        ),
        0.0,
        10.0,
    )
    momentum = _clamp(
        _get_numeric(
            payload.get("momentum"),
            defaults["momentum"],
            f"{axis_key}.momentum",
        ),
        -1.0,
        1.0,
    )
    premise_multiplier = _clamp(
        _get_numeric(
            payload.get("premise_multiplier"),
            defaults["premise_multiplier"],
            f"{axis_key}.premise_multiplier",
        ),
        0.0,
        10.0,
    )
    return {
        "average_level": average_level,
        "momentum": momentum,
        "premise_multiplier": premise_multiplier,
    }


def _coerce_content_axes(
    value: Any,
    base: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, float]]:
    if base:
        merged_base: dict[str, dict[str, float]] = {}
        for axis in CONTENT_AXIS_KEYS:
            axis_base = base.get(axis) if isinstance(base, Mapping) else None
            if isinstance(axis_base, ContentAxisSettings):
                axis_payload: Mapping[str, Any] = axis_base.as_dict()
            elif isinstance(axis_base, Mapping):
                axis_payload = axis_base
            else:
                axis_payload = {}
            merged_base[axis] = _sanitize_axis_payload(axis, axis_payload)
    else:
        merged_base = _content_axis_defaults()

    if value is None:
        return merged_base

    if isinstance(value, ContentAxisSettings):
        updates: Mapping[str, Any] = {axis: value.as_dict() for axis in CONTENT_AXIS_KEYS}
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:  # noqa: B904
            raise ValueError("content_axes must be valid JSON") from exc
        if not isinstance(parsed, Mapping):
            raise ValueError("content_axes must be a mapping")
        updates = parsed
    elif isinstance(value, Mapping):
        updates = value
    else:
        raise ValueError("content_axes must be a mapping")

    cleaned = merged_base
    for axis_key, axis_payload in updates.items():
        if axis_key not in _CONTENT_AXIS_KEY_SET:
            continue
        if isinstance(axis_payload, ContentAxisSettings):
            axis_mapping: Mapping[str, Any] = axis_payload.as_dict()
        elif isinstance(axis_payload, Mapping):
            axis_mapping = axis_payload
        else:
            raise ValueError(
                f"content axis '{axis_key}' must be a mapping of numeric values"
            )
        merged_payload = {**cleaned[axis_key], **axis_mapping}
        cleaned[axis_key] = _sanitize_axis_payload(axis_key, merged_payload)

    return cleaned


def _build_content_axis_settings(
    raw_axes: Mapping[str, Mapping[str, float]]
) -> dict[str, ContentAxisSettings]:
    settings: dict[str, ContentAxisSettings] = {}
    for axis_key in CONTENT_AXIS_KEYS:
        axis_values = raw_axes.get(axis_key, _DEFAULT_CONTENT_AXES[axis_key])
        settings[axis_key] = ContentAxisSettings(
            average_level=float(axis_values["average_level"]),
            momentum=float(axis_values["momentum"]),
            premise_multiplier=float(axis_values["premise_multiplier"]),
        )
    # Preserve any future additional axes that may be stored
    for axis_key, axis_values in raw_axes.items():
        if axis_key in settings:
            continue
        settings[axis_key] = ContentAxisSettings(
            average_level=float(axis_values["average_level"]),
            momentum=float(axis_values["momentum"]),
            premise_multiplier=float(axis_values["premise_multiplier"]),
        )
    return settings


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
    premise_prompt_refresh_interval: int
    premise_prompt_stats_window: int
    premise_prompt_variation_strength: float
    chaos_initial_min: float
    chaos_initial_max: float
    chaos_increment_min: float
    chaos_increment_max: float
    content_axes: dict[str, ContentAxisSettings]

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
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
            "premise_prompt_refresh_interval": self.premise_prompt_refresh_interval,
            "premise_prompt_stats_window": self.premise_prompt_stats_window,
            "premise_prompt_variation_strength": self.premise_prompt_variation_strength,
            "chaos_initial_min": self.chaos_initial_min,
            "chaos_initial_max": self.chaos_initial_max,
            "chaos_increment_min": self.chaos_increment_min,
            "chaos_increment_max": self.chaos_increment_max,
        }
        data["content_axes"] = {
            axis: settings.as_dict() for axis, settings in self.content_axes.items()
        }
        return data


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
    "premise_prompt_refresh_interval": {"type": int, "min": 1, "max": 200},
    "premise_prompt_stats_window": {"type": int, "min": 1, "max": 200},
    "premise_prompt_variation_strength": {"type": float, "min": 0.0, "max": 1.0},
    "chaos_initial_min": {"type": float, "min": 0.0, "max": 1.0},
    "chaos_initial_max": {"type": float, "min": 0.0, "max": 1.0},
    "chaos_increment_min": {"type": float, "min": 0.0, "max": 1.0},
    "chaos_increment_max": {"type": float, "min": 0.0, "max": 1.0},
    "content_axes": {"type": "content_axes", "default": _content_axis_defaults()},
}

_DEFAULTS: dict[str, Any] = {}
for key, meta in _CONFIG_SCHEMA.items():
    if key == "content_axes":
        _DEFAULTS[key] = _content_axis_defaults()
    else:
        _DEFAULTS[key] = getattr(_settings, key)


def _coerce_value(key: str, value: Any) -> Any:
    meta = _CONFIG_SCHEMA[key]
    target = meta["type"]
    if target == "content_axes":
        return _coerce_content_axes(value, _content_axis_defaults())
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
) -> dict[str, Any]:
    if not updates:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in updates.items():
        if key not in _CONFIG_SCHEMA:
            raise ValueError(f"Unknown configuration key: {key}")
        if key == "content_axes":
            current_axes = {
                axis: settings.as_dict()
                for axis, settings in current.content_axes.items()
            }
            cleaned[key] = _coerce_content_axes(value, current_axes)
            continue
        cleaned[key] = _coerce_value(key, value)

    min_active = cleaned.get("min_active_stories", current.min_active_stories)
    max_active = cleaned.get("max_active_stories", current.max_active_stories)
    if min_active > max_active:
        raise ValueError("min_active_stories cannot exceed max_active_stories")

    chaos_initial_min = cleaned.get("chaos_initial_min", current.chaos_initial_min)
    chaos_initial_max = cleaned.get("chaos_initial_max", current.chaos_initial_max)
    if chaos_initial_min > chaos_initial_max:
        raise ValueError("chaos_initial_min cannot exceed chaos_initial_max")

    chaos_increment_min = cleaned.get("chaos_increment_min", current.chaos_increment_min)
    chaos_increment_max = cleaned.get("chaos_increment_max", current.chaos_increment_max)
    if chaos_increment_min > chaos_increment_max:
        raise ValueError("chaos_increment_min cannot exceed chaos_increment_max")

    return cleaned


async def get_runtime_config(session: AsyncSession) -> RuntimeConfig:
    stmt = select(SystemConfig.key, SystemConfig.value)
    records = (await session.execute(stmt)).all()
    stored: dict[str, Any] = {key: value for key, value in records}

    scalar_values: dict[str, Any] = {}
    for key in _CONFIG_SCHEMA:
        if key == "content_axes":
            continue
        scalar_values[key] = _coerce_value(key, stored.get(key, _DEFAULTS[key]))

    raw_axes = _coerce_content_axes(
        stored.get("content_axes"),
        _DEFAULTS["content_axes"],
    )

    return RuntimeConfig(
        **scalar_values,
        content_axes=_build_content_axis_settings(raw_axes),
    )


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


__all__ = [
    "RuntimeConfig",
    "ContentAxisSettings",
    "CONTENT_AXIS_KEYS",
    "get_runtime_config",
    "apply_config_updates",
]
