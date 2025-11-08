import json
import logging
from typing import Any, Sequence

from openai import AsyncOpenAI, OpenAIError

from config import get_settings
from models import Chapter, Story

logger = logging.getLogger(__name__)

_settings = get_settings()
_client = AsyncOpenAI(api_key=_settings.openai_api_key)


async def evaluate_story(story: Story, chapters: Sequence[Chapter]) -> dict[str, Any]:
    chapter_summaries = "\n\n".join(
        f"Chapter {c.chapter_number}: {c.content[:4000]}"
        for c in chapters[-_settings.context_window_chapters :]
    )
    prompt = (
        f"Story: {story.title}\nPremise: {story.premise}\n"
        f"Recent chapters:\n{chapter_summaries}\n\n"
        "Evaluate this story's quality and viability.\n"
        "Score 0-10 on: coherence, novelty, engagement, pacing.\n"
        "Return JSON: {coherence_score, novelty_score, engagement_score, pacing_score, should_continue, reasoning, issues[]}\n"
        "Terminate if: repetitive, quality degraded, plot exhausted, stuck."
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

        # Check if this is a gpt-5 model - these don't support temperature
        # Try max_completion_tokens first (for newer models), fallback to max_tokens
        request_params = {
            "model": _settings.openai_eval_model,
            "messages": [
                {"role": "system", "content": "You are a story quality evaluator. Respond with JSON only."},
                {"role": "user", "content": prompt}
            ],
        }
        
        try:
            request_params["max_completion_tokens"] = effective_max_tokens
        except Exception:
            request_params["max_tokens"] = effective_max_tokens
        
        # Only add temperature for non-gpt-5 models
        if not is_gpt5_model:
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
    overall_score = (
        payload.get("coherence_score", 0.0) * weights.coherence
        + payload.get("novelty_score", 0.0) * weights.novelty
        + payload.get("engagement_score", 0.0) * weights.engagement
        + payload.get("pacing_score", 0.0) * weights.pacing
    )
    payload["overall_score"] = overall_score
    return payload


__all__ = ["evaluate_story"]
