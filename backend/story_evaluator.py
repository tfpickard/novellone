import json
import logging
from statistics import pstdev
from typing import Any, Sequence

from openai import AsyncOpenAI, OpenAIError

from config import get_settings
from models import Chapter, Story

logger = logging.getLogger(__name__)

_settings = get_settings()
_client = AsyncOpenAI(api_key=_settings.openai_api_key)


async def evaluate_story(story: Story, chapters: Sequence[Chapter], quality_threshold: float = 0.5) -> dict[str, Any]:
    """
    Evaluate a story's quality and determine if it should continue.

    Args:
        story: The story being evaluated
        chapters: All chapters of the story
        quality_threshold: Minimum overall score (0.0-1.0) required to continue (default: 0.5)
    """
    chapter_summaries = "\n\n".join(
        f"Chapter {c.chapter_number}: {c.content[:4000]}"
        for c in chapters[-_settings.context_window_chapters :]
    )

    # Convert threshold from 0-1 scale to 0-10 scale for the prompt
    threshold_0_10 = quality_threshold * 10.0

    prompt = (
        f"Story: {story.title}\nPremise: {story.premise}\n"
        f"Current chapter count: {story.chapter_count}\n"
        f"Recent chapters:\n{chapter_summaries}\n\n"
        "Evaluate this story's quality and viability.\n\n"
        "Score 0-10 on each dimension:\n"
        "- coherence: Is the plot logical and consistent? (0-3=incoherent, 4-6=some issues, 7-8=good, 9-10=excellent)\n"
        "- novelty: Is the story fresh and interesting? (0-3=derivative, 4-6=somewhat interesting, 7-8=creative, 9-10=highly original)\n"
        "- engagement: Would readers want to continue? (0-3=boring, 4-6=mildly interesting, 7-8=engaging, 9-10=captivating)\n"
        "- pacing: Does the story progress well? (0-3=stalled, 4-6=uneven, 7-8=good flow, 9-10=perfect pace)\n\n"
        f"Quality threshold: {threshold_0_10:.1f}/10 (overall weighted score)\n\n"
        "Set should_continue to FALSE if ANY of these critical issues apply:\n"
        "- Story is severely repetitive or going in circles\n"
        "- Plot has completely stalled or become incoherent\n"
        "- Story has completely lost its original premise or direction\n"
        "- Major continuity errors or severe logical inconsistencies\n"
        "- The story is fundamentally broken and cannot be salvaged\n\n"
        "Set should_continue to TRUE if the story is still viable and meeting the quality threshold.\n"
        "Minor issues, uneven pacing, or moderate quality are acceptable if above the threshold.\n\n"
        "Return ONLY valid JSON in this exact structure:\n"
        "{\n"
        '  "coherence_score": <0-10>,\n'
        '  "novelty_score": <0-10>,\n'
        '  "engagement_score": <0-10>,\n'
        '  "pacing_score": <0-10>,\n'
        '  "should_continue": <true/false>,\n'
        '  "reasoning": "Brief explanation of your decision",\n'
        '  "issues": ["issue1", "issue2"]\n'
        "}"
    )

    def _neutral_payload(reason: str) -> dict[str, Any]:
        logger.debug("Returning neutral evaluation payload: %s", reason)
        return {
            "coherence_score": 5.0,
            "novelty_score": 5.0,
            "engagement_score": 5.0,
            "pacing_score": 5.0,
            "should_continue": True,
            "reasoning": reason,
            "issues": [],
        }

    try:
        model_name = _settings.openai_eval_model.lower()
        is_reasoning_model = any(x in model_name for x in ["o1", "gpt-5", "reasoning"])
        is_gpt5_model = "gpt-5" in model_name

        # Reasoning models need more completion tokens (they spend many on internal reasoning).
        raw_max_tokens = _settings.openai_max_tokens_eval
        if is_reasoning_model:
            effective_max_tokens = min(raw_max_tokens * 5, 10000)
            logger.debug(
                "Reasoning eval model detected (%s); increasing token limit from %d to %d",
                _settings.openai_eval_model,
                raw_max_tokens,
                effective_max_tokens,
            )
        else:
            effective_max_tokens = raw_max_tokens

        # Build request parameters
        request_params = {
            "model": _settings.openai_eval_model,
            "messages": [
                {"role": "system", "content": "You are a story quality evaluator. Respond with JSON only."},
                {"role": "user", "content": prompt}
            ],
        }
        
        # Use max_completion_tokens for reasoning models (o1, gpt-5), max_tokens for others
        if is_reasoning_model:
            request_params["max_completion_tokens"] = effective_max_tokens
        else:
            request_params["max_tokens"] = effective_max_tokens
        
        # Only add temperature for non-gpt-5 and non-reasoning models
        if not is_gpt5_model and not is_reasoning_model:
            request_params["temperature"] = _settings.openai_temperature_eval
        
        response = await _client.chat.completions.create(**request_params)
    except OpenAIError as exc:
        logger.exception("OpenAI evaluation failed: %s", exc)
        raise

    if not response.choices:
        logger.error("Evaluation response had no choices: %s", response)
        payload = _neutral_payload("Evaluation response contained no choices.")
    else:
        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason == "content_filter":
            logger.error("Evaluation blocked by content filter for model %s", _settings.openai_eval_model)
            payload = _neutral_payload("Evaluation blocked by content filter.")
        else:
            message = getattr(choice, "message", None)
            content = ""
            if message is not None:
                content = getattr(message, "content", "") or ""
                if not content and hasattr(message, "text"):
                    content = getattr(message, "text") or ""
            content = content.strip() if isinstance(content, str) else str(content).strip()

            if not content:
                logger.warning(
                    "Evaluation response was empty. Finish reason=%s Usage=%s", finish_reason, getattr(response, "usage", None)
                )
                payload = _neutral_payload("Evaluation response was empty.")
            else:
                try:
                    payload = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("Evaluation response not JSON, providing neutral fallback")
                    payload = _neutral_payload(content)

    # Ensure required keys exist to avoid KeyError later
    payload.setdefault("coherence_score", 5.0)
    payload.setdefault("novelty_score", 5.0)
    payload.setdefault("engagement_score", 5.0)
    payload.setdefault("pacing_score", 5.0)
    payload.setdefault("should_continue", True)
    payload.setdefault("reasoning", "")
    payload.setdefault("issues", [])

    weights = _settings.evaluation_weights

    # Normalise individual dimensions to 0-1 range and guard against out-of-band
    # responses coming back from the model.
    dimensions = {
        "coherence": max(0.0, min(10.0, float(payload.get("coherence_score", 0.0)))) / 10.0,
        "novelty": max(0.0, min(10.0, float(payload.get("novelty_score", 0.0)))) / 10.0,
        "engagement": max(0.0, min(10.0, float(payload.get("engagement_score", 0.0)))) / 10.0,
        "pacing": max(0.0, min(10.0, float(payload.get("pacing_score", 0.0)))) / 10.0,
    }

    weighted_average = (
        dimensions["coherence"] * weights.coherence
        + dimensions["novelty"] * weights.novelty
        + dimensions["engagement"] * weights.engagement
        + dimensions["pacing"] * weights.pacing
    )

    dimension_values = tuple(dimensions.values())
    lowest_dimension = min(dimension_values)
    spread = pstdev(dimension_values) if len(dimension_values) > 1 else 0.0

    # Penalise lagging categories more aggressively once they dip beneath the
    # healthy band (roughly 8.5/10). This catches slumps before the average
    # masks them.
    weak_penalty = 0.0
    if lowest_dimension < 0.85:
        deficit = 0.85 - lowest_dimension
        weak_penalty = (deficit ** 1.2) * 1.2

    # Encourage balanced performance. High variance indicates one or more
    # dimensions are drifting far from the others.
    consistency_penalty = spread * 0.2

    # Each surfaced issue should count against the overall score so that
    # repeated soft warnings eventually trip the threshold.
    issue_penalty = min(len(payload.get("issues", [])) * 0.03, 0.15)

    # Reward exceptionally strong stories where every dimension is thriving,
    # keeping the upper range reachable.
    excellence_bonus = max(0.0, lowest_dimension - 0.92) * 0.1

    overall_score = weighted_average - weak_penalty - consistency_penalty - issue_penalty + excellence_bonus
    payload["overall_score_components"] = {
        "weighted_average": weighted_average,
        "weak_penalty": weak_penalty,
        "consistency_penalty": consistency_penalty,
        "issue_penalty": issue_penalty,
        "excellence_bonus": excellence_bonus,
    }
    payload["overall_score"] = max(0.0, min(1.0, overall_score))
    return payload


__all__ = ["evaluate_story"]
