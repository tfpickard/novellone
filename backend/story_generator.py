import json
import logging
import random
import re
import time
from collections import Counter
from datetime import datetime
from statistics import mean
from typing import Any, Sequence

from openai import AsyncOpenAI, OpenAIError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_settings
from config_store import RuntimeConfig, get_runtime_config
from database import get_session
from models import Chapter, Story, SystemConfig

logger = logging.getLogger(__name__)

_settings = get_settings()
_client = AsyncOpenAI(api_key=_settings.openai_api_key)

_PROMPT_STATE_KEY = "premise_prompt_state"
_MAX_DYNAMIC_DIRECTIVES = 4
_SUMMARY_MODEL = "gpt-5-nano"

_HURLLOL_LEXICON: dict[str, tuple[str, ...]] = {
    "H": (
        "Hyperdimensional",
        "Holographic",
        "Haunted",
        "Heliospheric",
        "Hypersigil",
    ),
    "U": (
        "Uplink",
        "Unstable",
        "Ultraviolet",
        "Uncanny",
        "Utopian",
    ),
    "R": (
        "Resonance",
        "Rift",
        "Recombinator",
        "Runic",
        "Relay",
    ),
    "L": (
        "Laboratory",
        "Lattice",
        "Liminal",
        "Loom",
        "Launch",
    ),
    "O": (
        "Oracle",
        "Outpost",
        "Orbit",
        "Operator",
        "Overmind",
    ),
}


def _generate_hurllol_title() -> tuple[str, list[str]]:
    words: list[str] = []
    for letter in "HURLLOL":
        options = _HURLLOL_LEXICON.get(letter, (letter,))
        choice = random.choice(options)
        words.append(choice)
    title = " ".join(words)
    return title, words


def _safe_mean(values: Sequence[float]) -> float:
    return float(mean(values)) if values else 0.0


def _clean_directives(directives: Sequence[str]) -> list[str]:
    cleaned = [d.strip() for d in directives if isinstance(d, str) and d.strip()]
    return cleaned[:_MAX_DYNAMIC_DIRECTIVES]


def _render_premise_prompt(
    style_instruction: str, directives: Sequence[str]
) -> str:
    cleaned_directives = _clean_directives(directives)
    directives_block = ""
    if cleaned_directives:
        directive_lines = "\n".join(f"- {line}" for line in cleaned_directives)
        directives_block = (
            "\nDynamic variation objectives (embrace novelty over safety, even if scores dip a little):\n"
            f"{directive_lines}\n"
        )

    return (
        "Generate a unique, creative science fiction story premise.\n\n"
        "Requirements:\n"
        "- Create a completely unique, memorable title (NEVER use generic titles like 'Untitled Expedition', 'The Unknown Journey', 'Unknown', etc.)\n"
        "- Be highly creative: explore unusual, surreal, disturbing, or mind-bending sci-fi concepts\n"
        "- Include a character named Tom who is an engineer (can be major or minor role)\n"
        "- Each story must be completely unique and different from any previous story\n"
        "- Each story must be somewhat absurd, ridiculous and surreal. Choose how much of each randomly.\n"
        "- Write a detailed, engaging premise (2-3 sentences minimum)\n"
        f"{style_instruction}\n"
        "- DO NOT mention these authors by name in the title or premise\n"
        "- Let their influence guide the tone, perspective, themes, and narrative approach\n"
        f"{directives_block}\n"
        "Respond with ONLY valid JSON in this exact structure (no markdown code blocks, no extra text):\n\n"
        "{\n"
        '  "title": "Your Unique Creative Title",\n'
        '  "premise": "A detailed, engaging premise that describes the story concept",\n'
        '  "themes": ["theme1", "theme2"],\n'
        '  "setting": "Brief setting description",\n'
        '  "central_conflict": "The main conflict or problem",\n'
        '  "narrative_perspective": "first-person" or "third-person-limited" or "third-person-omniscient" or "second-person",\n'
        '  "tone": "A brief description of the story tone (e.g., dark, humorous, philosophical, melancholic, satirical, etc.)",\n'
        '  "genre_tags": ["tag1", "tag2", "tag3"] // Additional genre/style descriptors like "existential", "noir", "absurdist", "dystopian", etc.\n'
        "}\n\n"
        "Example titles for inspiration (create something different):\n"
        "- Echoes of the Quantum Conductor\n"
        "- The Symphony of Interfaces\n"
        "- Resonance of the Distant Past\n"
        "- Neural Labyrinth Protocol\n"
        "- Cathedral of Borrowed Futures\n"
        "- The Recursion Architects"
    )


async def _summarize_recent_story_stats(session, window: int) -> dict[str, Any]:
    if window <= 0:
        return {
            "recent_story_count": 0,
            "average_overall_score": 0.0,
            "overall_score_span": None,
            "most_common_tones": [],
            "most_common_perspectives": [],
            "most_common_genre_tags": [],
            "frequent_style_authors": [],
            "avg_absurdity_initial": 0.0,
            "avg_absurdity_increment": 0.0,
            "avg_surrealism_initial": 0.0,
            "avg_surrealism_increment": 0.0,
            "avg_ridiculousness_initial": 0.0,
            "avg_ridiculousness_increment": 0.0,
            "avg_insanity_initial": 0.0,
            "avg_insanity_increment": 0.0,
            "sample_titles": [],
        }

    stmt = (
        select(Story)
        .order_by(Story.created_at.desc())
        .limit(window)
        .options(selectinload(Story.evaluations))
    )
    stories = list((await session.execute(stmt)).scalars())
    story_count = len(stories)
    if story_count == 0:
        return await _summarize_recent_story_stats(session, 0)

    tones: Counter[str] = Counter()
    perspectives: Counter[str] = Counter()
    genres: Counter[str] = Counter()
    authors: Counter[str] = Counter()

    absurdity_initials: list[float] = []
    absurdity_increments: list[float] = []
    surrealism_initials: list[float] = []
    surrealism_increments: list[float] = []
    ridiculousness_initials: list[float] = []
    ridiculousness_increments: list[float] = []
    insanity_initials: list[float] = []
    insanity_increments: list[float] = []
    overall_scores: list[float] = []

    for story in stories:
        if story.tone:
            tones[story.tone.lower()] += 1
        if story.narrative_perspective:
            perspectives[story.narrative_perspective.lower()] += 1
        if story.genre_tags:
            genres.update(tag.lower() for tag in story.genre_tags if isinstance(tag, str))
        if story.style_authors:
            authors.update(author for author in story.style_authors if isinstance(author, str))

        if story.absurdity_initial is not None:
            absurdity_initials.append(float(story.absurdity_initial))
        if story.absurdity_increment is not None:
            absurdity_increments.append(float(story.absurdity_increment))
        if story.surrealism_initial is not None:
            surrealism_initials.append(float(story.surrealism_initial))
        if story.surrealism_increment is not None:
            surrealism_increments.append(float(story.surrealism_increment))
        if story.ridiculousness_initial is not None:
            ridiculousness_initials.append(float(story.ridiculousness_initial))
        if story.ridiculousness_increment is not None:
            ridiculousness_increments.append(float(story.ridiculousness_increment))
        if story.insanity_initial is not None:
            insanity_initials.append(float(story.insanity_initial))
        if story.insanity_increment is not None:
            insanity_increments.append(float(story.insanity_increment))

        if story.evaluations:
            latest_eval = max(story.evaluations, key=lambda e: e.chapter_number)
            if latest_eval.overall_score is not None:
                overall_scores.append(float(latest_eval.overall_score))

    stats = {
        "recent_story_count": story_count,
        "average_overall_score": round(_safe_mean(overall_scores), 3),
        "overall_score_span": (
            [round(min(overall_scores), 3), round(max(overall_scores), 3)]
            if overall_scores
            else None
        ),
        "most_common_tones": [tone for tone, _ in tones.most_common(5)],
        "most_common_perspectives": [p for p, _ in perspectives.most_common(5)],
        "most_common_genre_tags": [tag for tag, _ in genres.most_common(8)],
        "frequent_style_authors": [author for author, _ in authors.most_common(8)],
        "avg_absurdity_initial": round(_safe_mean(absurdity_initials), 3),
        "avg_absurdity_increment": round(_safe_mean(absurdity_increments), 3),
        "avg_surrealism_initial": round(_safe_mean(surrealism_initials), 3),
        "avg_surrealism_increment": round(_safe_mean(surrealism_increments), 3),
        "avg_ridiculousness_initial": round(_safe_mean(ridiculousness_initials), 3),
        "avg_ridiculousness_increment": round(_safe_mean(ridiculousness_increments), 3),
        "avg_insanity_initial": round(_safe_mean(insanity_initials), 3),
        "avg_insanity_increment": round(_safe_mean(insanity_increments), 3),
        "sample_titles": [story.title for story in stories[:5] if story.title],
        "generated_at": datetime.utcnow().isoformat(),
    }
    return stats


def _fallback_prompt_variation(stats: dict[str, Any]) -> dict[str, Any]:
    directives: list[str] = []
    tones = stats.get("most_common_tones") or []
    perspectives = stats.get("most_common_perspectives") or []
    genres = stats.get("most_common_genre_tags") or []

    if tones:
        directives.append(
            "Deliberately choose a tone that contrasts with recent favourites such as "
            + ", ".join(tones[:3])
            + "; explore an unexpected emotional register."
        )
    if perspectives:
        directives.append(
            "Switch narrative perspective away from common picks like "
            + ", ".join(perspectives[:2])
            + "; try something unusual or hybrid."
        )
    if genres:
        directives.append(
            "Invent new genre tags or mashups instead of repeating "
            + ", ".join(genres[:4])
            + "."
        )

    if not directives:
        directives.append(
            "Inject a wild conceptual twist that bends the premise structure (e.g., nonlinear timelines, meta-fiction, or bizarre constraints)."
        )

    rationale = (
        "Generated heuristics locally because the prompt remix model was unavailable."
    )
    return {"directives": directives[:_MAX_DYNAMIC_DIRECTIVES], "rationale": rationale}


async def _call_prompt_engineer(prompt: str, *, temperature: float) -> str:
    model = _settings.openai_eval_model
    model_lower = model.lower()
    is_reasoning_model = any(x in model_lower for x in ["o1", "gpt-5", "reasoning"])
    request_params: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an inventive prompt designer who specialises in keeping creative systems surprising and dynamic.",
            },
            {"role": "user", "content": prompt},
        ],
    }

    max_tokens = min(800, _settings.openai_max_tokens_eval)
    if is_reasoning_model:
        request_params["max_completion_tokens"] = min(max_tokens * 2, 4000)
    else:
        request_params["max_tokens"] = max_tokens

    if "gpt-5" not in model_lower and not is_reasoning_model:
        request_params["temperature"] = temperature

    response = await _client.chat.completions.create(**request_params)
    if not response.choices:
        raise RuntimeError("Prompt engineer response contained no choices")

    choice = response.choices[0]
    message = getattr(choice, "message", None)
    content = ""
    if message is not None:
        content = getattr(message, "content", "") or ""
        if not content and hasattr(message, "text"):
            content = getattr(message, "text") or ""

    content = content.strip() if isinstance(content, str) else str(content).strip()
    if not content:
        raise RuntimeError("Prompt engineer response was empty")

    return content


async def _request_prompt_variation_from_model(
    stats: dict[str, Any], variation_strength: float
) -> dict[str, Any]:
    stats_json = json.dumps(stats, indent=2, sort_keys=True)
    prompt_lines = [
        "We run an autonomous sci-fi story generator. The base prompt already demands unique titles, surreal energy, an engineer named Tom, and JSON output.",
        "We care about variation more than maximising average quality scores. Use the recent story metrics below to propose new creative pushes.",
        f"Variation strength: {variation_strength:.2f} (0 = gentle, 1 = extremely bold).",
        "",
        "Recent story snapshot (most recent first):",
        stats_json,
        "",
        "Provide 2-4 concise imperative directives that we can append to the base prompt to shake things up.",
        "The directives must not remove existing requirements (e.g., keep Tom the engineer, keep JSON structure) but should introduce fresh experiments.",
        "Encourage swings into underexplored tones, structures, settings, or narrative devices.",
        "Then explain your reasoning in <=80 words.",
        "",
        "Return only valid JSON: {\"directives\": [\"directive1\", ...], \"rationale\": \"brief explanation\"}.",
    ]
    prompt = "\n".join(prompt_lines)

    temperature = 0.35 + (variation_strength * 0.45)
    raw = await _call_prompt_engineer(prompt, temperature=temperature)
    parsed = _safe_json_loads(raw)
    if not parsed:
        raise ValueError("Prompt engineer response was not valid JSON")
    return parsed


async def _ensure_prompt_state(session, config) -> tuple[dict[str, Any], bool]:
    row = await session.get(SystemConfig, _PROMPT_STATE_KEY)
    state: dict[str, Any] = {}
    if row and isinstance(row.value, dict):
        state = dict(row.value)

    total_story_count = (
        await session.execute(select(func.count()).select_from(Story))
    ).scalar_one()
    last_story_count = int(state.get("story_count_at_refresh", 0))
    refresh_interval = max(1, int(config.premise_prompt_refresh_interval))
    stories_since_refresh = total_story_count - last_story_count
    needs_refresh = not state or stories_since_refresh >= refresh_interval

    if not needs_refresh:
        return state, False

    stats = await _summarize_recent_story_stats(
        session, int(config.premise_prompt_stats_window)
    )
    variation_strength = max(0.0, min(1.0, float(config.premise_prompt_variation_strength)))
    try:
        variation = await _request_prompt_variation_from_model(stats, variation_strength)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Prompt remix request failed, using fallback directives: %s", exc)
        variation = _fallback_prompt_variation(stats)

    directives = _clean_directives(variation.get("directives", []))
    if not directives:
        fallback = _fallback_prompt_variation(stats)
        directives = _clean_directives(fallback.get("directives", []))
        variation["rationale"] = variation.get("rationale") or fallback.get("rationale")

    hurllol_title, hurllol_components = _generate_hurllol_title()

    state = {
        "directives": directives,
        "rationale": variation.get("rationale", ""),
        "generated_at": datetime.utcnow().isoformat(),
        "story_count_at_refresh": int(total_story_count),
        "stats_snapshot": stats,
        "variation_strength": variation_strength,
        "hurllol_title": hurllol_title,
        "hurllol_title_components": hurllol_components,
        "hurllol_title_generated_at": datetime.utcnow().isoformat(),
    }

    if row is None:
        row = SystemConfig(key=_PROMPT_STATE_KEY, value=state)
        session.add(row)
    else:
        row.value = state

    await session.flush()
    logger.info(
        "Updated premise prompt directives (stories_since_refresh=%d, directives=%s)",
        stories_since_refresh,
        directives,
    )
    return state, True


async def _load_current_prompt_state() -> dict[str, Any]:
    config = None
    async with get_session() as session:
        config = await get_runtime_config(session)
        state, _ = await _ensure_prompt_state(session, config)
        await session.commit()
    if not state:
        strength = (
            float(config.premise_prompt_variation_strength)
            if config is not None
            else 0.6
        )
        return {"directives": [], "variation_strength": strength}
    return state


async def get_premise_prompt_state(session: AsyncSession) -> dict[str, Any]:
    config = await get_runtime_config(session)
    state, _ = await _ensure_prompt_state(session, config)
    if not state:
        strength = float(config.premise_prompt_variation_strength)
        return {"directives": [], "variation_strength": strength}
    needs_hurllol_bootstrap = not state.get("hurllol_title")
    if needs_hurllol_bootstrap:
        title, components = _generate_hurllol_title()
        patched = dict(state)
        patched.update(
            {
                "hurllol_title": title,
                "hurllol_title_components": components,
                "hurllol_title_generated_at": datetime.utcnow().isoformat(),
            }
        )
        row = await session.get(SystemConfig, _PROMPT_STATE_KEY)
        if row is None:
            row = SystemConfig(key=_PROMPT_STATE_KEY, value=patched)
            session.add(row)
        else:
            row.value = patched
        await session.flush()
        return patched
    return state


async def update_premise_prompt_state(
    session: AsyncSession,
    *,
    directives: Sequence[str] | None = None,
    rationale: str | None = None,
) -> dict[str, Any]:
    state = await get_premise_prompt_state(session)
    updated = dict(state)
    changed = False
    now = datetime.utcnow().isoformat()

    if directives is not None:
        cleaned = _clean_directives(directives)
        updated["directives"] = cleaned
        updated["generated_at"] = now
        updated["manual_override"] = True
        changed = True

    if rationale is not None:
        updated["rationale"] = rationale.strip()
        updated["manual_override"] = True
        changed = True

    if not changed:
        return updated

    row = await session.get(SystemConfig, _PROMPT_STATE_KEY)
    if row is None:
        row = SystemConfig(key=_PROMPT_STATE_KEY, value=updated)
        session.add(row)
    else:
        row.value = updated

    await session.flush()
    return updated


async def get_hurllol_banner(session: AsyncSession) -> dict[str, Any]:
    state = await get_premise_prompt_state(session)
    raw_components = state.get("hurllol_title_components") or []
    components = [str(component) for component in raw_components]
    return {
        "title": state.get("hurllol_title"),
        "components": components,
        "generated_at": state.get("hurllol_title_generated_at"),
    }


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


async def generate_story_premise(config: RuntimeConfig) -> dict[str, Any]:
    # Generate random chaos parameters for this story
    initial_min = float(config.chaos_initial_min)
    initial_max = float(config.chaos_initial_max)
    increment_min = float(config.chaos_increment_min)
    increment_max = float(config.chaos_increment_max)

    absurdity_initial = random.uniform(initial_min, initial_max)
    surrealism_initial = random.uniform(initial_min, initial_max)
    ridiculousness_initial = random.uniform(initial_min, initial_max)
    insanity_initial = random.uniform(initial_min, initial_max)

    absurdity_increment = random.uniform(increment_min, increment_max)
    surrealism_increment = random.uniform(increment_min, increment_max)
    ridiculousness_increment = random.uniform(increment_min, increment_max)
    insanity_increment = random.uniform(increment_min, increment_max)

    logger.info(
        "Generated chaos parameters: absurdity=%.3f+%.3f, surrealism=%.3f+%.3f, ridiculousness=%.3f+%.3f, insanity=%.3f+%.3f",
        absurdity_initial, absurdity_increment,
        surrealism_initial, surrealism_increment,
        ridiculousness_initial, ridiculousness_increment,
        insanity_initial, insanity_increment,
    )

    # List of famous 20th century authors with distinctive styles
    famous_authors = [
        "Franz Kafka", "Jorge Luis Borges", "Italo Calvino", "Gabriel García Márquez",
        "Kurt Vonnegut", "Philip K. Dick", "Ursula K. Le Guin", "Stanisław Lem",
        "Samuel Beckett", "Virginia Woolf", "James Joyce", "William S. Burroughs",
        "Haruki Murakami", "Octavia Butler", "Ray Bradbury", "Isaac Asimov",
        "J.G. Ballard", "William Gibson", "Margaret Atwood", "Aldous Huxley",
        "George Orwell", "Arthur C. Clarke", "Doris Lessing", "Thomas Pynchon",
        "Don DeLillo", "Chinua Achebe", "Toni Morrison", "Gabriel García Márquez",
        "Salman Rushdie", "Milan Kundera", "Cormac McCarthy", "Vladimir Nabokov"
    ]

    # Randomly select 1-3 authors
    num_authors = random.randint(1, 3)
    selected_authors = random.sample(famous_authors, num_authors)

    logger.info("Selected style authors: %s", selected_authors)

    # Build style instruction
    if len(selected_authors) == 1:
        style_instruction = f"- Adopt the writing style and sensibilities of {selected_authors[0]}"
    else:
        authors_list = ", ".join(selected_authors[:-1]) + f", and {selected_authors[-1]}"
        style_instruction = f"- Blend the writing styles and sensibilities of {authors_list}"

    prompt_state = await _load_current_prompt_state()
    directives = prompt_state.get("directives", []) if isinstance(prompt_state, dict) else []
    prompt = _render_premise_prompt(style_instruction, directives)
    raw_strength = (
        prompt_state.get("variation_strength")
        if isinstance(prompt_state, dict)
        else None
    )
    try:
        variation_strength_value = float(raw_strength) if raw_strength is not None else 0.0
    except (TypeError, ValueError):
        variation_strength_value = 0.0
    logger.debug(
        "Premise prompt directives applied: %s (variation_strength=%.2f)",
        directives,
        variation_strength_value,
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
                    # Add style authors
                    parsed["style_authors"] = selected_authors
                    parsed["prompt_directives"] = directives
                    parsed["prompt_variation_strength"] = prompt_state.get(
                        "variation_strength"
                    )
                    parsed["prompt_variation_rationale"] = prompt_state.get("rationale")
                    parsed["prompt_directives_generated_at"] = prompt_state.get(
                        "generated_at"
                    )
                    # Ensure metadata fields exist
                    if "narrative_perspective" not in parsed:
                        parsed["narrative_perspective"] = "third-person-limited"
                    if "tone" not in parsed:
                        parsed["tone"] = "mysterious"
                    if "genre_tags" not in parsed:
                        parsed["genre_tags"] = []
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
                "narrative_perspective": "third-person-limited",
                "tone": "mysterious",
                "genre_tags": [],
                "prompt_directives": directives,
                "prompt_variation_strength": prompt_state.get("variation_strength"),
                "prompt_variation_rationale": prompt_state.get("rationale"),
                "prompt_directives_generated_at": prompt_state.get("generated_at"),
                "style_authors": selected_authors,
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
        "narrative_perspective": "third-person-limited",
        "tone": "mysterious",
        "genre_tags": [],
        "prompt_directives": directives,
        "prompt_variation_strength": prompt_state.get("variation_strength"),
        "prompt_variation_rationale": prompt_state.get("rationale"),
        "prompt_directives_generated_at": prompt_state.get("generated_at"),
        "style_authors": selected_authors,
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


async def generate_story_summary(story: Story, chapters: Sequence[Chapter]) -> str:
    if not chapters:
        return ""

    excerpts: list[str] = []
    for chapter in chapters:
        excerpt = chapter.content.strip()
        if len(excerpt) > 1500:
            excerpt = excerpt[:1500].rstrip() + "…"
        excerpts.append(f"Chapter {chapter.chapter_number}: {excerpt}")

    context_block = "\n\n".join(excerpts)
    prompt = (
        f"Title: {story.title}\n"
        f"Premise: {story.premise}\n\n"
        "Write a concise recap of the story so far using the chapter excerpts below."
        " Summarise major arcs, conflicts, and character developments in 3-4 sentences."
        " Mention Tom the engineer if relevant. Keep it factual and avoid spoilers beyond the provided chapters.\n\n"
        f"Chapter excerpts:\n{context_block}"
    )

    try:
        response = await _client.chat.completions.create(
            model=_SUMMARY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise story analyst who writes spoiler-free recaps.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.2,
        )
    except OpenAIError as exc:
        logger.exception("Failed to generate story summary for %s: %s", story.title, exc)
        return ""

    if not response.choices:
        logger.warning("Summary response returned no choices for story %s", story.title)
        return ""

    message = response.choices[0].message
    content = getattr(message, "content", None) or getattr(message, "text", "")
    summary = content.strip() if isinstance(content, str) else str(content).strip()
    return summary


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
            # If decoding fails, continue with the original text; not all inputs are valid JSON.
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
    story_summary: str | None = None,
    finale: bool = False,
    completion_reason: str | None = None,
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

    summary_section = ""
    if story_summary:
        summary_section = (
            "Continuity summary (keep this consistent even if older events fall outside the chapter context):\n"
            f"{story_summary}\n\n"
        )

    # Build style instruction if authors are specified
    style_instruction = ""
    if story.style_authors and len(story.style_authors) > 0:
        if len(story.style_authors) == 1:
            style_instruction = f"\nSTYLE GUIDE: Write in the style and sensibilities of {story.style_authors[0]}. Do not mention this author by name in the text.\n"
        else:
            authors_list = ", ".join(story.style_authors[:-1]) + f", and {story.style_authors[-1]}"
            style_instruction = f"\nSTYLE GUIDE: Blend the writing styles and sensibilities of {authors_list}. Do not mention these authors by name in the text.\n"

    # Add narrative perspective and tone guidance if available
    metadata_guidance = ""
    if story.narrative_perspective:
        metadata_guidance += f"Narrative perspective: {story.narrative_perspective}\n"
    if story.tone:
        metadata_guidance += f"Tone: {story.tone}\n"

    finale_instruction = ""
    if finale:
        finale_instruction = (
            "\nThis chapter is the story conclusion. Resolve central conflicts, pay off the premise,"
            " and leave readers with a sense of completion while honouring lingering mysteries."
        )
        if completion_reason:
            finale_instruction += f" The story is ending because: {completion_reason}."

    prompt = (
        f"Story: {story.title}\n"
        f"Premise: {story.premise}\n"
        f"{summary_section}"
        f"Previous chapters: {context or 'None yet.'}\n"
        f"{style_instruction}"
        f"{metadata_guidance}\n"
        f"Write Chapter {chapter_number}. Continue naturally, develop characters/plot, introduce complications.\n"
        "Aim for 600-900 words and ensure the chapter forms a coherent arc with a beginning, middle, and end."
        " Do not end mid-sentence; conclude with a strong beat or hook."
        f"{finale_instruction}\n\n"
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


async def spawn_new_story(config: RuntimeConfig) -> dict[str, Any]:
    premise_data = await generate_story_premise(config)
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
    "generate_story_summary",
    "generate_chapter",
    "generate_cover_image",
    "spawn_new_story",
    "get_premise_prompt_state",
    "update_premise_prompt_state",
    "get_hurllol_banner",
]
