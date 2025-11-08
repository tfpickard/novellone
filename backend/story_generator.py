import json
import logging
import time
from typing import Any, Sequence

from openai import AsyncOpenAI, OpenAIError

from config import get_settings
from models import Chapter, Story

logger = logging.getLogger(__name__)

_settings = get_settings()
_client = AsyncOpenAI(api_key=_settings.openai_api_key)


async def _call_openai(
    model: str, prompt: str, *, max_tokens: int, temperature: float
) -> tuple[str, dict[str, int] | None]:
    try:
        response = await _client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=max_tokens,
            # temperature=temperature,
        )
    except OpenAIError as exc:
        logger.exception("OpenAI request failed: %s", exc)
        raise

    usage: dict[str, int] | None = None
    response_usage = getattr(response, "usage", None)
    if response_usage is not None:
        if hasattr(response_usage, "model_dump"):
            usage = {
                key: int(value)
                for key, value in response_usage.model_dump().items()
                if isinstance(value, (int, float))
            }
        elif isinstance(response_usage, dict):
            usage = {
                key: int(value)
                for key, value in response_usage.items()
                if isinstance(value, (int, float))
            }
        else:
            extracted: dict[str, int] = {}
            for key in ("output_tokens", "input_tokens", "total_tokens", "completion_tokens"):
                value = getattr(response_usage, key, None)
                if isinstance(value, (int, float)):
                    extracted[key] = int(value)
            usage = extracted or None

    text = getattr(response, "output_text", None)
    if text:
        return text, usage

    output = getattr(response, "output", None)
    if not output:
        raise RuntimeError("OpenAI response was empty")

    if output[0].type == "message":
        return output[0].content[0].text, usage
    text_output = "".join(
        part.content[0].text if getattr(part, "type", None) == "message" else ""
        for part in output
        if hasattr(part, "content")
    )
    return text_output, usage


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Try to recover a JSON object from model output.

    The Responses API sometimes wraps JSON in prose or Markdown code fences. This helper
    extracts the first balanced JSON object it can find and parses it. If no valid JSON is
    present, ``None`` is returned.
    """

    candidates: list[str] = []

    trimmed = text.strip()
    if trimmed:
        candidates.append(trimmed)

    fence_start = trimmed.find("```")
    if fence_start != -1:
        fence_end = trimmed.rfind("```")
        if fence_end != -1 and fence_end > fence_start:
            inner = trimmed[fence_start + 3 : fence_end]
            inner = inner.lstrip("json\n\r ")
            inner = inner.strip()
            if inner:
                candidates.append(inner)

    start = text.find("{")
    while start != -1:
        depth = 0
        end = start
        while end < len(text):
            char = text[end]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start : end + 1].strip())
                    break
            end += 1
        start = text.find("{", start + 1)

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _safe_json_loads(text: str) -> dict[str, Any] | None:
    result = None
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = _extract_json_object(text)
    return result


async def generate_story_premise() -> dict[str, Any]:
    prompt = (
        "Generate a unique, compelling science fiction story premise. Be creative and "
        "explore unusual, surreal and disturbing concepts.\n"
        "Include a character named Tom who is an engineer to the story. He can be a major or minor character.\n"
        "Return JSON: {title, premise, themes[], setting, central_conflict}\n"
        'Examples: "Von Neumann probes develop culture", "Time dilation prison", "Sentient Dyson sphere"'
    )
    try:
        text, _ = await _call_openai(
            _settings.openai_premise_model,
            prompt,
            max_tokens=_settings.openai_max_tokens_premise,
            temperature=_settings.openai_temperature_premise,
        )
        logger.debug("Raw premise response: %s", text[:200])
        parsed = _safe_json_loads(text)
        if parsed is not None:
            logger.info("Successfully generated premise: %s", parsed.get("title", "Unknown"))
            return parsed
        logger.warning("Premise response not JSON, wrapping text. Response: %s", text[:500])
        return {
            "title": "Untitled Expedition",
            "premise": text.strip(),
            "themes": [],
            "setting": "Unknown",
            "central_conflict": "Unclear",
        }
    except Exception as exc:
        logger.exception("Failed to generate premise: %s", exc)
        raise


async def generate_story_theme(premise: str, title: str) -> dict[str, Any]:
    prompt = (
        f"Based on {title!r} and the following premise: {premise}\n"
        "generate a visual theme matching the story's tone/setting.\n"
        "Return JSON with exact structure: {primary_color, secondary_color, background_color, text_color, "
        "text_secondary, accent_color, border_color, card_background, font_heading, font_body, aesthetic, mood, "
        "border_radius, shadow_style, animation_speed}.\n"
        "Make colors harmonious and readable. Choose fonts that match aesthetic."
    )
    text, _ = await _call_openai(
        _settings.openai_premise_model,
        prompt,
        max_tokens=_settings.openai_max_tokens_premise,
        temperature=_settings.openai_temperature_premise,
    )
    parsed = _safe_json_loads(text)
    if parsed is not None:
        return parsed
    logger.warning("Theme response not JSON, providing fallback theme")
    return {
        "primary_color": "#1f2933",
        "secondary_color": "#3d5a80",
        "background_color": "#0f172a",
        "text_color": "#f8fafc",
        "text_secondary": "#cbd5f5",
        "accent_color": "#e0fbfc",
        "border_color": "#1e293b",
        "card_background": "#16213e",
        "font_heading": "Orbitron, sans-serif",
        "font_body": "Inter, sans-serif",
        "aesthetic": "fallback",
        "mood": "mysterious",
        "border_radius": "12px",
        "shadow_style": "0 12px 32px rgba(15, 23, 42, 0.45)",
        "animation_speed": "0.4s",
    }


_TERMINATING_PUNCTUATION = {".", "!", "?", "…"}
_CLOSING_PUNCTUATION = {"'", '"', "”", "’", "]", ")", "»"}


def _needs_conclusion(text: str) -> bool:
    trimmed = text.rstrip()
    if not trimmed:
        return False
    while trimmed and trimmed[-1] in _CLOSING_PUNCTUATION:
        trimmed = trimmed[:-1]
    if not trimmed:
        return False
    if trimmed.endswith("..."):
        return False
    return trimmed[-1] not in _TERMINATING_PUNCTUATION


async def _complete_chapter(story: Story, draft: str) -> str:
    completion_prompt = (
        f"Story: {story.title}\n"
        f"Premise: {story.premise}\n"
        "The following chapter draft ended abruptly."
        " Continue it with a concise concluding section (1-2 paragraphs)"
        " that resolves the immediate scene while preserving tension for future chapters."
        " Maintain the same perspective, tone, and pacing, and do not repeat existing text.\n\n"
        "Chapter draft so far:\n"
        f"{draft}\n\n"
        "Write only the new concluding text."
    )
    max_tokens = max(256, int(_settings.openai_max_tokens_chapter * 0.35))
    addition, _ = await _call_openai(
        _settings.openai_model,
        completion_prompt,
        max_tokens=max_tokens,
        temperature=_settings.openai_temperature_chapter,
    )
    separator = "\n\n" if not draft.endswith("\n\n") else "\n"
    return f"{draft.rstrip()}{separator}{addition.strip()}"


async def generate_chapter(
    story: Story,
    recent_chapters: Sequence[Chapter],
    *,
    chapter_number: int,
) -> dict[str, Any]:
    context = "\n\n".join(
        f"Chapter {chapter.chapter_number}: {chapter.content}"
        for chapter in recent_chapters
    )
    prompt = (
        f"Story: {story.title}\n"
        f"Premise: {story.premise}\n"
        f"Previous chapters: {context or 'None yet.'}\n"
        f"Write Chapter {chapter_number}. Continue naturally, develop characters/plot, introduce complications.\n"
        "Aim for 600-900 words and ensure the chapter forms a coherent arc with a beginning, middle, and end."
        " Do not end mid-sentence; conclude with a strong beat or hook."
    )
    start = time.perf_counter()
    text, usage = await _call_openai(
        _settings.openai_model,
        prompt,
        max_tokens=_settings.openai_max_tokens_chapter,
        temperature=_settings.openai_temperature_chapter,
    )
    if _needs_conclusion(text):
        text = await _complete_chapter(story, text)
    elapsed = int((time.perf_counter() - start) * 1000)
    tokens_used: int | None = None
    if usage:
        tokens_used = (
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or usage.get("total_tokens")
        )
    return {
        "chapter_number": chapter_number,
        "content": text.strip(),
        "tokens_used": tokens_used,
        "generation_time_ms": elapsed,
        "model_used": _settings.openai_model,
    }


async def generate_cover_image(story_title: str, story_premise: str) -> str:
    """Generate a cover image for a completed story using DALL-E.
    
    Returns the URL of the generated image.
    """
    # Create a concise, visual prompt for DALL-E based on the story
    prompt = (
        f"Book cover art for a science fiction story titled '{story_title}'. "
        f"Story premise: {story_premise[:200]}... "
        "Create a striking, atmospheric cover image with a cinematic composition. "
        "Style: modern sci-fi book cover, professional, dramatic lighting, no text."
    )
    
    logger.info("Generating cover image for story: %s", story_title)
    logger.debug("Cover image prompt: %s", prompt[:300])
    
    try:
        response = await _client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            logger.info("✓ Successfully generated cover image for: %s - URL: %s", story_title, image_url[:50])
            return image_url
        else:
            logger.warning("✗ No image data returned for story: %s", story_title)
            return ""
    except OpenAIError as exc:
        logger.exception("✗ OpenAI error generating cover image for %s: %s", story_title, exc)
        return ""
    except Exception as exc:
        logger.exception("✗ Unexpected error generating cover image for %s: %s", story_title, exc)
        return ""


async def spawn_new_story() -> dict[str, Any]:
    premise_data = await generate_story_premise()
    title = premise_data.get("title") or "Untitled Expedition"
    premise = premise_data.get("premise") or "A mysterious journey unfolds."
    theme = await generate_story_theme(premise, title)
    return {
        "title": title,
        "premise": premise,
        "theme_json": theme,
        "premise_payload": premise_data,
    }


__all__ = [
    "generate_story_premise",
    "generate_story_theme",
    "generate_chapter",
    "generate_cover_image",
    "spawn_new_story",
]
