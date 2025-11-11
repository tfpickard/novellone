from __future__ import annotations

import os

import pytest

_ENV_DEFAULTS = {
    "DATABASE_URL": "sqlite+aiosqlite://",
    "OPENAI_API_KEY": "test-key",
    "OPENAI_MODEL": "gpt-4-turbo",
    "OPENAI_PREMISE_MODEL": "gpt-4-turbo",
    "OPENAI_EVAL_MODEL": "gpt-4-turbo",
    "OPENAI_MAX_TOKENS_CHAPTER": "1024",
    "OPENAI_MAX_TOKENS_PREMISE": "1024",
    "OPENAI_MAX_TOKENS_EVAL": "1024",
    "OPENAI_TEMPERATURE_CHAPTER": "0.7",
    "OPENAI_TEMPERATURE_PREMISE": "0.7",
    "OPENAI_TEMPERATURE_EVAL": "0.7",
    "PREMISE_PROMPT_REFRESH_INTERVAL": "5",
    "PREMISE_PROMPT_STATS_WINDOW": "8",
    "PREMISE_PROMPT_VARIATION_STRENGTH": "0.5",
    "CHAPTER_INTERVAL_SECONDS": "30",
    "EVALUATION_INTERVAL_CHAPTERS": "3",
    "WORKER_TICK_INTERVAL": "15",
    "MIN_ACTIVE_STORIES": "2",
    "MAX_ACTIVE_STORIES": "4",
    "CONTEXT_WINDOW_CHAPTERS": "6",
    "MAX_CHAPTERS_PER_STORY": "12",
    "MIN_CHAPTERS_BEFORE_EVAL": "2",
    "QUALITY_SCORE_MIN": "0.6",
    "COHERENCE_WEIGHT": "0.25",
    "NOVELTY_WEIGHT": "0.25",
    "ENGAGEMENT_WEIGHT": "0.25",
    "PACING_WEIGHT": "0.25",
}

for key, value in _ENV_DEFAULTS.items():
    os.environ.setdefault(key, value)

from config_store import (
    CONTENT_AXIS_KEYS,
    ContentAxisSettings,
    _coerce_content_axes,
    _content_axis_defaults,
)


def test_coerce_content_axes_returns_defaults_for_missing_payload() -> None:
    defaults = _content_axis_defaults()

    result = _coerce_content_axes(None)

    assert result == defaults
    assert set(result) == set(CONTENT_AXIS_KEYS)
    for axis, values in result.items():
        assert values == defaults[axis]


def test_coerce_content_axes_clamps_values_outside_ranges() -> None:
    payload = {
        "sexual_content": {
            "average_level": 27,
            "momentum": -5,
            "premise_multiplier": 18,
        },
        "violence": {
            "average_level": -3,
            "momentum": 3,
            "premise_multiplier": -4,
        },
    }

    result = _coerce_content_axes(payload)

    assert result["sexual_content"] == {
        "average_level": 10.0,
        "momentum": -1.0,
        "premise_multiplier": 10.0,
    }
    assert result["violence"] == {
        "average_level": 0.0,
        "momentum": 1.0,
        "premise_multiplier": 0.0,
    }


def test_coerce_content_axes_merges_with_base_settings() -> None:
    base = {
        "sexual_content": {
            "average_level": 4.5,
            "momentum": 0.25,
            "premise_multiplier": 1.5,
        },
        "violence": {
            "average_level": 7.0,
            "momentum": -0.5,
            "premise_multiplier": 2.0,
        },
    }
    update = {
        "sexual_content": {"momentum": 0.75},
        "violence": {"average_level": 12},
    }

    result = _coerce_content_axes(update, base)

    assert result["sexual_content"] == {
        "average_level": 4.5,
        "momentum": 0.75,
        "premise_multiplier": 1.5,
    }
    # average_level is clamped while other fields fall back to base
    assert result["violence"] == {
        "average_level": 10.0,
        "momentum": -0.5,
        "premise_multiplier": 2.0,
    }


def test_coerce_content_axes_rejects_non_numeric_values() -> None:
    payload = {"sexual_content": {"average_level": "heavy"}}

    with pytest.raises(ValueError):
        _coerce_content_axes(payload)


def test_content_axis_settings_round_trip_from_object() -> None:
    overrides = {
        axis: ContentAxisSettings(average_level=axis_idx, momentum=0.1, premise_multiplier=2.0)
        for axis_idx, axis in enumerate(CONTENT_AXIS_KEYS, start=1)
    }

    result = _coerce_content_axes(overrides)

    for axis, values in result.items():
        expected = overrides[axis].as_dict()
        assert values == expected
