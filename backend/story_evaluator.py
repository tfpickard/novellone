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
        f"Current chapter count: {story.chapter_count}\n"
        f"Recent chapters:\n{chapter_summaries}\n\n"
        "Evaluate this story's quality and viability with STRICT criteria.\n\n"
        "Score 0-10 on each dimension:\n"
        "- coherence: Is the plot logical and consistent? (Be strict: 0-3=incoherent, 4-6=some issues, 7-8=good, 9-10=excellent)\n"
        "- novelty: Is the story fresh and interesting? (Be strict: 0-3=derivative, 4-6=somewhat interesting, 7-8=creative, 9-10=highly original)\n"
        "- engagement: Would readers want to continue? (Be strict: 0-3=boring, 4-6=mildly interesting, 7-8=engaging, 9-10=captivating)\n"
        "- pacing: Does the story progress well? (Be strict: 0-3=stalled, 4-6=uneven, 7-8=good flow, 9-10=perfect pace)\n\n"
        "IMPORTANT: Be HARSH in your evaluation. Most stories should NOT continue.\n"
        "Set should_continue to FALSE if ANY of these apply:\n"
        "- Story is repetitive or going in circles\n"
        "- Quality has degraded from earlier chapters\n"
        "- Plot feels exhausted or forced\n"
        "- Story has lost its original premise or direction\n"
        "- Characters are acting inconsistently without good reason\n"
        "- Pacing has stalled or become meandering\n"
        "- Any score is below 5.0\n"
        "- Overall quality is merely 'okay' rather than 'good' or 'excellent'\n"
        "- Story has exceeded 10 chapters without significant plot development\n\n"
        "Return ONLY valid JSON in this exact structure:\n"
        "{\n"
        '  "coherence_score": <0-10>,\n'
        '  "novelty_score": <0-10>,\n'
        '  "engagement_score": <0-10>,\n'
        '  "pacing_score": <0-10>,\n'
        '  "should_continue": <true/false>,\n'
        '  "reasoning": "Brief explanation of your decision",\n'
        '  "issues": ["issue1", "issue2"]\n'
        "}\n\n"
        "Remember: Most stories should be terminated. Only truly exceptional stories should continue."
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
    # Scores are on 0-10 scale, so we normalize to 0-1 by dividing by 10
    overall_score = (
        payload.get("coherence_score", 0.0) * weights.coherence
        + payload.get("novelty_score", 0.0) * weights.novelty
        + payload.get("engagement_score", 0.0) * weights.engagement
        + payload.get("pacing_score", 0.0) * weights.pacing
    ) / 10.0
    payload["overall_score"] = overall_score
    return payload


__all__ = ["evaluate_story"]
