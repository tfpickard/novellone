import json
import logging
import random
import re
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
    """Call OpenAI API using Chat Completions endpoint."""
    try:
        # Check if this is a reasoning model (o1, gpt-5-mini, etc.)
        # Reasoning models need much higher token limits because they use tokens for internal reasoning
        is_reasoning_model = any(
            x in model.lower() for x in ["o1", "gpt-5", "reasoning"]
        )

        # Check if this is a gpt-5 model - these don't support temperature at all
        is_gpt5_model = "gpt-5" in model.lower()

        # For reasoning models, increase token limit significantly
        # They use ~80% of tokens for reasoning, so we need 5x the desired output
        # But cap at reasonable limits to avoid API errors
        if is_reasoning_model:
            # Cap at 16k tokens max for reasoning models (API limit is usually 16k-32k)
            effective_max_tokens = min(max_tokens * 5, 16000)
            logger.debug(
                "Reasoning model detected (%s), increasing token limit from %d to %d",
                model,
                max_tokens,
                effective_max_tokens,
            )
        else:
            effective_max_tokens = max_tokens

        # Build request parameters
        request_params = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a creative science fiction writer who generates unique story ideas in JSON format.",
                },
                {"role": "user", "content": prompt},
            ],
        }

        # Use max_completion_tokens for reasoning models (o1, gpt-5), max_tokens for others
        if is_reasoning_model:
            request_params["max_completion_tokens"] = effective_max_tokens
        else:
            request_params["max_tokens"] = effective_max_tokens

        # Only add temperature for non-gpt-5 and non-reasoning models
        # GPT-5 and o1 models don't support temperature parameter
        if not is_gpt5_model and not is_reasoning_model:
            request_params["temperature"] = temperature

        response = await _client.chat.completions.create(**request_params)
    except OpenAIError as exc:
        logger.exception("OpenAI request failed: %s", exc)
        raise

    usage: dict[str, int] | None = None
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    if not response.choices or len(response.choices) == 0:
        logger.error("OpenAI response had no choices. Response: %s", response)
        raise RuntimeError("OpenAI response had no choices")

    choice = response.choices[0]
    message = choice.message

    # Check finish_reason for issues
    finish_reason = getattr(choice, "finish_reason", None)
    if finish_reason == "content_filter":
        logger.error("OpenAI response was filtered. Model: %s", model)
        raise RuntimeError("OpenAI response was filtered by content policy")
    elif finish_reason == "length":
        # Check if this is a reasoning model that used all tokens for reasoning
        usage_details = getattr(response.usage, "completion_tokens_details", None)
        if usage_details:
            reasoning_tokens = getattr(usage_details, "reasoning_tokens", 0)
            accepted_tokens = getattr(usage_details, "accepted_prediction_tokens", 0)
            if reasoning_tokens > 0 and accepted_tokens == 0:
                logger.error(
                    "Reasoning model %s used all tokens for reasoning (%d), none for output. Increase max_completion_tokens.",
                    model,
                    reasoning_tokens,
                )
                raise RuntimeError(
                    f"Model used all {reasoning_tokens} tokens for reasoning, none left for output. Increase max_completion_tokens."
                )
        logger.warning(
            "OpenAI response was truncated due to length. Model: %s, Finish reason: %s",
            model,
            finish_reason,
        )
        # Continue anyway - partial content is better than nothing

    if not message:
        logger.error(
            "OpenAI response message was None. Response: %s, Finish reason: %s",
            response,
            finish_reason,
        )
        raise RuntimeError("OpenAI response message was None")

    # Handle different response formats
    content = None
    if hasattr(message, "content"):
        content = message.content
    elif hasattr(message, "text"):
        content = message.text
    elif hasattr(message, "text_content"):
        content = message.text_content

    if not content:
        logger.error(
            "OpenAI response message content was empty. Message: %s, Finish reason: %s, Response: %s",
            message,
            finish_reason,
            response,
        )
        raise RuntimeError("OpenAI response message was empty")

    content_str = content.strip() if isinstance(content, str) else str(content).strip()
    if not content_str:
        logger.error(
            "OpenAI response message content was empty after stripping. Original: %s, Finish reason: %s",
            content,
            finish_reason,
        )
        raise RuntimeError("OpenAI response message was empty")

    return content_str, usage


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Try to recover a JSON object from model output.

    The Responses API sometimes wraps JSON in prose or Markdown code fences. This helper
    extracts the first balanced JSON object it can find and parses it. If no valid JSON is
    present, ``None`` is returned.
    """
    if not text or not text.strip():
        return None

    candidates: list[str] = []

    trimmed = text.strip()
    if trimmed:
        candidates.append(trimmed)

    # Try to extract from markdown code fences
    fence_start = trimmed.find("```")
    if fence_start != -1:
        fence_end = trimmed.rfind("```")
        if fence_end != -1 and fence_end > fence_start:
            inner = trimmed[fence_start + 3 : fence_end]
            # Remove language identifier (json, jsonc, etc.)
            inner = re.sub(r"^json[^\n]*\n?", "", inner, flags=re.IGNORECASE)
            inner = inner.strip()
            if inner:
                candidates.append(inner)

    # Try to find JSON objects by matching braces
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
                    json_candidate = text[start : end + 1].strip()
                    candidates.append(json_candidate)
                    break
            end += 1
        start = text.find("{", start + 1)

    # Try each candidate
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
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
    # Generate random chaos parameters for this story
    absurdity_initial = random.uniform(0.05, 0.25)
    surrealism_initial = random.uniform(0.05, 0.25)
    ridiculousness_initial = random.uniform(0.05, 0.25)
    insanity_initial = random.uniform(0.05, 0.25)
    
    absurdity_increment = random.uniform(0.02, 0.15)
    surrealism_increment = random.uniform(0.02, 0.15)
    ridiculousness_increment = random.uniform(0.02, 0.15)
    insanity_increment = random.uniform(0.02, 0.15)
    
    logger.info(
        "Generated chaos parameters: absurdity=%.3f+%.3f, surrealism=%.3f+%.3f, ridiculousness=%.3f+%.3f, insanity=%.3f+%.3f",
        absurdity_initial, absurdity_increment,
        surrealism_initial, surrealism_increment,
        ridiculousness_initial, ridiculousness_increment,
        insanity_initial, insanity_increment,
    )
    
    # More explicit prompt with stronger instructions
    prompt = (
        "Generate a unique, creative science fiction story premise.\n\n"
        "Requirements:\n"
        "- Create a completely unique, memorable title (NEVER use generic titles like 'Untitled Expedition', 'The Unknown Journey', 'Unknown', etc.)\n"
        "- Be highly creative: explore unusual, surreal, disturbing, or mind-bending sci-fi concepts\n"
        "- Include a character named Tom who is an engineer (can be major or minor role)\n"
        "- Each story must be completely unique and different from any previous story\n"
        "- Each story must be somewhat absurd, ridiculous and surreal. Choose how much of each randomly.\n"
        "- Write a detailed, engaging premise (2-3 sentences minimum)\n\n"
        "Respond with ONLY valid JSON in this exact structure (no markdown code blocks, no extra text):\n\n"
        "{\n"
        '  "title": "Your Unique Creative Title",\n'
        '  "premise": "A detailed, engaging premise that describes the story concept",\n'
        '  "themes": ["theme1", "theme2"],\n'
        '  "setting": "Brief setting description",\n'
        '  "central_conflict": "The main conflict or problem"\n'
        "}\n\n"
        "Example titles for inspiration (create something different):\n"
        "- Echoes of the Quantum Conductor\n"
        "- The Symphony of Interfaces\n"
        "- Resonance of the Distant Past\n"
        "- Neural Labyrinth Protocol\n"
        "- Cathedral of Borrowed Futures\n"
        "- The Recursion Architects"
    )

    max_retries = 2
    for attempt in range(max_retries):
        try:
            text, _ = await _call_openai(
                _settings.openai_premise_model,
                prompt,
                max_tokens=_settings.openai_max_tokens_premise,
                temperature=_settings.openai_temperature_premise,
            )
            logger.debug(
                "Raw premise response (attempt %d, first 500 chars): %s",
                attempt + 1,
                text[:500],
            )

            # Try to parse JSON
            parsed = _safe_json_loads(text)
            if parsed is not None:
                # Validate required fields
                title = parsed.get("title", "").strip()
                premise = parsed.get("premise", "").strip()

                # Reject generic fallback titles
                if title.lower() in (
                    "untitled expedition",
                    "the unknown journey",
                    "untitled",
                    "unknown journey",
                ):
                    logger.warning("Rejected generic title '%s', retrying...", title)
                    if attempt < max_retries - 1:
                        continue
                    # Last attempt failed, generate unique title
                    title = f"Story {int(time.time()) % 100000}"

                if title and premise:
                    logger.info("✓ Successfully generated premise: '%s'", title)
                    # Add chaos parameters to the response
                    parsed["absurdity_initial"] = absurdity_initial
                    parsed["surrealism_initial"] = surrealism_initial
                    parsed["ridiculousness_initial"] = ridiculousness_initial
                    parsed["insanity_initial"] = insanity_initial
                    parsed["absurdity_increment"] = absurdity_increment
                    parsed["surrealism_increment"] = surrealism_increment
                    parsed["ridiculousness_increment"] = ridiculousness_increment
                    parsed["insanity_increment"] = insanity_increment
                    return parsed
                else:
                    logger.warning(
                        "Parsed JSON missing required fields. Title: %s, Premise: %s",
                        bool(title),
                        bool(premise),
                    )

            # If JSON parsing failed, try to extract title and premise from text
            logger.warning(
                "JSON parsing failed (attempt %d). Attempting to extract from text. Response: %s",
                attempt + 1,
                text[:500],
            )

            # Try to extract title from common patterns
            title_match = None
            premise_text = text.strip()

            # Look for patterns like "Title: ..." or quoted titles
            title_patterns = [
                r'"title"\s*:\s*"([^"]+)"',
                r"'title'\s*:\s*'([^']+)'",
                r'Title:\s*"?([^"\n]+)"?',
                r"#\s*([^\n]+)",  # Markdown header
            ]

            for pattern in title_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    title_match = match.group(1).strip()
                    # Reject generic titles
                    if title_match.lower() not in (
                        "untitled expedition",
                        "the unknown journey",
                        "untitled",
                        "unknown journey",
                    ):
                        break
                    title_match = None

            # If we found a title, use it; otherwise generate one from the premise
            if title_match:
                title = title_match
            else:
                # Generate a unique title from the premise text
                words = [
                    w for w in premise_text.split()[:8] if w.isalnum() and len(w) > 2
                ]
                if words:
                    title = " ".join(word.capitalize() for word in words[:4])
                else:
                    title = f"Story {int(time.time()) % 100000}"

            logger.info("Generated fallback premise with title: '%s'", title)
            return {
                "title": title,
                "premise": premise_text
                if premise_text
                else "A mysterious journey unfolds.",
                "themes": [],
                "setting": "Unknown",
                "central_conflict": "Unclear",
                "absurdity_initial": absurdity_initial,
                "surrealism_initial": surrealism_initial,
                "ridiculousness_initial": ridiculousness_initial,
                "insanity_initial": insanity_initial,
                "absurdity_increment": absurdity_increment,
                "surrealism_increment": surrealism_increment,
                "ridiculousness_increment": ridiculousness_increment,
                "insanity_increment": insanity_increment,
            }
        except Exception as exc:
            logger.exception(
                "Failed to generate premise (attempt %d): %s", attempt + 1, exc
            )
            if attempt < max_retries - 1:
                continue

    # All retries failed - return unique fallback
    fallback_title = f"Story {int(time.time()) % 100000}"
    logger.warning(
        "All attempts failed. Using emergency fallback title: %s", fallback_title
    )
    return {
        "title": fallback_title,
        "premise": "A mysterious journey unfolds.",
        "themes": [],
        "setting": "Unknown",
        "central_conflict": "Unclear",
        "absurdity_initial": absurdity_initial,
        "surrealism_initial": surrealism_initial,
        "ridiculousness_initial": ridiculousness_initial,
        "insanity_initial": insanity_initial,
        "absurdity_increment": absurdity_increment,
        "surrealism_increment": surrealism_increment,
        "ridiculousness_increment": ridiculousness_increment,
        "insanity_increment": insanity_increment,
    }


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


def _clean_chapter_content(raw: str) -> str:
    if not raw:
        return raw

    text = raw.strip()

    # Handle JSON string payload (quoted)
    if text.startswith('"') and text.endswith('"'):
        try:
            decoded = json.loads(text)
            if isinstance(decoded, str):
                text = decoded.strip()
        except json.JSONDecodeError:
            pass

    # Handle nested JSON object containing chapter_content
    if text.startswith("{") and text.endswith("}"):
        nested = _safe_json_loads(text)
        if nested and isinstance(nested, dict):
            inner = nested.get("chapter_content")
            if isinstance(inner, str):
                return inner.strip()

    # Remove trailing JSON-like metrics block if present
    if '"absurdity"' in text and '"chapter_content"' not in text:
        lines = text.splitlines()
        cleaned_lines: list[str] = []
        for line in lines:
            if line.strip().startswith('"absurdity"'):
                break
            cleaned_lines.append(line)
        text = "\n".join(cleaned_lines).strip()

    return text


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
    # Calculate expected chaos parameters for this chapter
    expected_absurdity = story.absurdity_initial + (chapter_number - 1) * story.absurdity_increment
    expected_surrealism = story.surrealism_initial + (chapter_number - 1) * story.surrealism_increment
    expected_ridiculousness = story.ridiculousness_initial + (chapter_number - 1) * story.ridiculousness_increment
    expected_insanity = story.insanity_initial + (chapter_number - 1) * story.insanity_increment
    
    logger.info(
        "Chapter %d chaos parameters: absurdity=%.3f, surrealism=%.3f, ridiculousness=%.3f, insanity=%.3f",
        chapter_number,
        expected_absurdity,
        expected_surrealism,
        expected_ridiculousness,
        expected_insanity,
    )
    
    context = "\n\n".join(
        f"Chapter {chapter.chapter_number}: {chapter.content}"
        for chapter in recent_chapters
    )
    
    prompt = (
        f"Story: {story.title}\n"
        f"Premise: {story.premise}\n"
        f"Previous chapters: {context or 'None yet.'}\n\n"
        f"Write Chapter {chapter_number}. Continue naturally, develop characters/plot, introduce complications.\n"
        "Aim for 600-900 words and ensure the chapter forms a coherent arc with a beginning, middle, and end."
        " Do not end mid-sentence; conclude with a strong beat or hook.\n\n"
        f"CHAOS PARAMETERS for this chapter (scale 0.0-1.0):\n"
        f"- Absurdity: {expected_absurdity:.3f} (logical inconsistencies, bizarre situations)\n"
        f"- Surrealism: {expected_surrealism:.3f} (dreamlike, symbolic, reality-bending elements)\n"
        f"- Ridiculousness: {expected_ridiculousness:.3f} (comedic absurdity, over-the-top scenarios)\n"
        f"- Insanity: {expected_insanity:.3f} (chaotic, unhinged, breaking conventions)\n\n"
        "Write the chapter with these parameters in mind, making it progressively more chaotic as specified.\n\n"
        "After writing the chapter, respond with ONLY valid JSON in this exact structure:\n"
        "{\n"
        '  "chapter_content": "Your full chapter text here...",\n'
        f'  "absurdity": {expected_absurdity:.3f},\n'
        f'  "surrealism": {expected_surrealism:.3f},\n'
        f'  "ridiculousness": {expected_ridiculousness:.3f},\n'
        f'  "insanity": {expected_insanity:.3f}\n'
        "}\n\n"
        "Return the EXACT chaos parameter values provided above in your response."
    )
    
    start = time.perf_counter()
    text, usage = await _call_openai(
        _settings.openai_model,
        prompt,
        max_tokens=_settings.openai_max_tokens_chapter,
        temperature=_settings.openai_temperature_chapter,
    )
    
    # Try to parse JSON response
    parsed = _safe_json_loads(text)
    chapter_content = text.strip()
    actual_absurdity = expected_absurdity
    actual_surrealism = expected_surrealism
    actual_ridiculousness = expected_ridiculousness
    actual_insanity = expected_insanity
    
    if parsed and isinstance(parsed, dict):
        chapter_content = parsed.get("chapter_content", text.strip())
        actual_absurdity = parsed.get("absurdity", expected_absurdity)
        actual_surrealism = parsed.get("surrealism", expected_surrealism)
        actual_ridiculousness = parsed.get("ridiculousness", expected_ridiculousness)
        actual_insanity = parsed.get("insanity", expected_insanity)
        logger.info(
            "✓ Chapter %d generated with chaos parameters from OpenAI response",
            chapter_number
        )
    else:
        logger.warning(
            "Failed to parse chapter JSON response, using text as-is and expected chaos values"
        )
    
    chapter_content = _clean_chapter_content(chapter_content)

    if _needs_conclusion(chapter_content):
        chapter_content = await _complete_chapter(story, chapter_content)
    
    elapsed = int((time.perf_counter() - start) * 1000)
    tokens_used: int | None = None
    if usage:
        tokens_used = usage.get("completion_tokens") or usage.get("total_tokens")
    
    return {
        "chapter_number": chapter_number,
        "content": chapter_content.strip(),
        "tokens_used": tokens_used,
        "generation_time_ms": elapsed,
        "model_used": _settings.openai_model,
        "absurdity": actual_absurdity,
        "surrealism": actual_surrealism,
        "ridiculousness": actual_ridiculousness,
        "insanity": actual_insanity,
    }


async def generate_cover_image(story_title: str, story_premise: str) -> str:
    """Generate a cover image for a completed story using DALL-E.

    Returns the URL of the generated image, or empty string on failure.
    """
    # Create a concise, visual prompt for DALL-E based on the story
    # Limit premise to avoid prompt length issues
    premise_summary = story_premise[:200] if len(story_premise) > 200 else story_premise

    prompt = (
        f"Book cover art for a science fiction story titled '{story_title}'. "
        f"Story premise: {premise_summary}. "
        "Create a striking, atmospheric cover image with a cinematic composition. "
        "Style: modern sci-fi book cover, professional, dramatic lighting. "
        f"Render the title text '{story_title}' clearly within the artwork, integrating it into the scene with polished typography."
    )

    logger.info("Generating cover image for story: %s", story_title)
    logger.debug("Cover image prompt length: %d chars", len(prompt))

    try:
        response = await _client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        if not response:
            logger.warning("✗ Empty response from DALL-E for story: %s", story_title)
            return ""

        if not hasattr(response, "data") or not response.data:
            logger.warning(
                "✗ No data attribute in DALL-E response for story: %s", story_title
            )
            return ""

        if len(response.data) == 0:
            logger.warning(
                "✗ Empty data array in DALL-E response for story: %s", story_title
            )
            return ""

        image_obj = response.data[0]
        image_url = getattr(image_obj, "url", None)
        if image_url and image_url.startswith("http"):
            logger.info(
                "✓ Successfully generated cover image for: %s - URL: %s",
                story_title,
                image_url[:60],
            )
            return image_url

        b64_data = getattr(image_obj, "b64_json", None)
        if b64_data:
            data_url = f"data:image/png;base64,{b64_data}"
            logger.info(
                "✓ Generated cover image (base64) for: %s",
                story_title,
            )
            return data_url

        logger.warning("✗ No image URL or base64 data returned for story: %s", story_title)
        return ""

    except OpenAIError as exc:
        logger.exception(
            "✗ OpenAI error generating cover image for %s: %s", story_title, exc
        )
        return ""
    except AttributeError as exc:
        logger.exception(
            "✗ Attribute error generating cover image for %s: %s", story_title, exc
        )
        return ""
    except Exception as exc:
        logger.exception(
            "✗ Unexpected error generating cover image for %s: %s", story_title, exc
        )
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
        # Extract chaos parameters from premise_data
        "absurdity_initial": premise_data.get("absurdity_initial", 0.1),
        "surrealism_initial": premise_data.get("surrealism_initial", 0.1),
        "ridiculousness_initial": premise_data.get("ridiculousness_initial", 0.1),
        "insanity_initial": premise_data.get("insanity_initial", 0.1),
        "absurdity_increment": premise_data.get("absurdity_increment", 0.05),
        "surrealism_increment": premise_data.get("surrealism_increment", 0.05),
        "ridiculousness_increment": premise_data.get("ridiculousness_increment", 0.05),
        "insanity_increment": premise_data.get("insanity_increment", 0.05),
    }


__all__ = [
    "generate_story_premise",
    "generate_story_theme",
    "generate_chapter",
    "generate_cover_image",
    "spawn_new_story",
]
