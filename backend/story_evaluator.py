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
        f"Chapter {c.chapter_number}: {c.content[:4000]}" for c in chapters[-_settings.context_window_chapters :]
    )
    prompt = (
        f"Story: {story.title}\nPremise: {story.premise}\n"
        f"Recent chapters:\n{chapter_summaries}\n\n"
        "Evaluate this story's quality and viability.\n"
        "Score 0-10 on: coherence, novelty, engagement, pacing.\n"
        "Return JSON: {coherence_score, novelty_score, engagement_score, pacing_score, should_continue, reasoning, issues[]}\n"
        "Terminate if: repetitive, quality degraded, plot exhausted, stuck."
    )
    try:
        response = await _client.responses.create(
            model=_settings.openai_eval_model,
            input=prompt,
            max_output_tokens=_settings.openai_max_tokens_eval,
            temperature=_settings.openai_temperature_eval,
        )
    except OpenAIError as exc:
        logger.exception("OpenAI evaluation failed: %s", exc)
        raise

    text = getattr(response, 'output_text', None)
    if text is None:
        output = getattr(response, 'output', None)
        if not output:
            raise RuntimeError('Empty evaluation response')
        if output[0].type == 'message':
            text = output[0].content[0].text
        else:
            text = ''.join(
                part.content[0].text if getattr(part, 'type', None) == 'message' else ''
                for part in output
                if hasattr(part, 'content')
            )

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Evaluation response not JSON, providing neutral fallback")
        payload = {
            "coherence_score": 5.0,
            "novelty_score": 5.0,
            "engagement_score": 5.0,
            "pacing_score": 5.0,
            "should_continue": True,
            "reasoning": text,
            "issues": [],
        }

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
