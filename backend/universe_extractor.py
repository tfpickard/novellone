"""Universe extraction service for mining shared elements from stories."""

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Chapter, Story, UniverseElement, UniversePrompt
from story_generator import _call_openai

logger = logging.getLogger(__name__)


async def extract_universe_from_stories(
    session: AsyncSession,
    universe_prompt_id: UUID,
    story_ids: list[UUID],
) -> None:
    """
    Extract universe elements from selected stories and populate the universe prompt.

    This function:
    1. Loads all chapters from the selected stories
    2. Calls OpenAI to analyze and extract shared elements
    3. Populates characters, settings, themes, and lore in the universe prompt
    4. Creates individual UniverseElement records for tracking
    """
    # Load universe prompt
    prompt_stmt = select(UniversePrompt).where(UniversePrompt.id == universe_prompt_id)
    universe_prompt = (await session.execute(prompt_stmt)).scalar_one()

    # Load all stories with their chapters
    story_stmt = (
        select(Story)
        .where(Story.id.in_(story_ids))
        .options(selectinload(Story.chapters))
    )
    stories = (await session.execute(story_stmt)).scalars().all()

    if not stories:
        logger.warning("No stories found for extraction")
        return

    # Prepare story content for analysis
    story_data = []
    for story in stories:
        chapters_text = "\n\n".join(
            f"Chapter {c.chapter_number}:\n{c.content}" for c in story.chapters
        )
        story_data.append({
            "story_id": str(story.id),
            "title": story.title,
            "premise": story.premise,
            "chapters": chapters_text,
        })

    # Call OpenAI to extract universe elements
    extraction_result = await _extract_elements_with_llm(story_data)

    if not extraction_result:
        logger.error("Failed to extract universe elements")
        return

    # Update universe prompt with extracted data
    universe_prompt.characters = extraction_result.get("characters", {})
    universe_prompt.settings = extraction_result.get("settings", {})
    universe_prompt.themes = extraction_result.get("themes", {})
    universe_prompt.lore = extraction_result.get("lore", {})
    universe_prompt.narrative_constraints = extraction_result.get("narrative_constraints", [])
    universe_prompt.version += 1

    # Create UniverseElement records for each extracted item
    for story in stories:
        # Characters
        for char_name, char_data in extraction_result.get("characters", {}).items():
            element = UniverseElement(
                universe_prompt_id=universe_prompt_id,
                source_story_id=story.id,
                element_type="character",
                name=char_name,
                description=char_data.get("description", ""),
                element_metadata=char_data,
            )
            session.add(element)

        # Settings
        for setting_name, setting_data in extraction_result.get("settings", {}).items():
            element = UniverseElement(
                universe_prompt_id=universe_prompt_id,
                source_story_id=story.id,
                element_type="setting",
                name=setting_name,
                description=setting_data.get("description", ""),
                element_metadata=setting_data,
            )
            session.add(element)

        # Themes
        for theme_name, theme_data in extraction_result.get("themes", {}).items():
            element = UniverseElement(
                universe_prompt_id=universe_prompt_id,
                source_story_id=story.id,
                element_type="theme",
                name=theme_name,
                description=theme_data.get("description", ""),
                element_metadata=theme_data,
            )
            session.add(element)

        # Lore
        for lore_topic, lore_data in extraction_result.get("lore", {}).items():
            element = UniverseElement(
                universe_prompt_id=universe_prompt_id,
                source_story_id=story.id,
                element_type="lore",
                name=lore_topic,
                description=lore_data.get("description", ""),
                element_metadata=lore_data,
            )
            session.add(element)

    await session.flush()
    logger.info(
        "Extracted universe elements from %d stories into prompt '%s'",
        len(stories),
        universe_prompt.name,
    )


async def _extract_elements_with_llm(story_data: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Use OpenAI to analyze stories and extract shared universe elements.

    Returns a structured dict with:
    - characters: {name: {traits, background, relationships}}
    - settings: {name: {description, rules, history}}
    - themes: {theme: {description, examples}}
    - lore: {topic: {facts, constraints}}
    - narrative_constraints: [rules for future stories]
    """
    # Prepare the analysis prompt
    stories_summary = "\n\n".join(
        f"=== Story: {s['title']} ===\n"
        f"Premise: {s['premise']}\n\n"
        f"{s['chapters'][:10000]}"  # Limit to first 10k chars per story to stay within token limits
        for s in story_data
    )

    prompt = f"""Analyze the following stories and extract shared universe elements that could be reused in future stories within this universe.

{stories_summary}

Extract and structure the following:

1. **Characters**: Recurring or significant characters with their traits, backgrounds, and relationships
2. **Settings**: Locations, worlds, or environments with their descriptions, rules, and history
3. **Themes**: Recurring themes, motifs, or concepts with descriptions and examples
4. **Lore**: World-building facts, magic systems, technology, or historical events
5. **Narrative Constraints**: Rules or patterns that should guide future stories in this universe

Return a JSON object with this exact structure:
{{
  "characters": {{
    "character_name": {{
      "description": "brief description",
      "traits": ["trait1", "trait2"],
      "background": "background info",
      "relationships": {{"other_character": "relationship"}}
    }}
  }},
  "settings": {{
    "setting_name": {{
      "description": "detailed description",
      "rules": ["rule1", "rule2"],
      "history": "historical context"
    }}
  }},
  "themes": {{
    "theme_name": {{
      "description": "theme description",
      "examples": ["example1", "example2"]
    }}
  }},
  "lore": {{
    "topic": {{
      "description": "lore description",
      "facts": ["fact1", "fact2"],
      "constraints": ["constraint1"]
    }}
  }},
  "narrative_constraints": [
    "constraint or pattern that should be followed",
    "another constraint"
  ]
}}

Focus on elements that:
- Appear across multiple stories or are central to the universe
- Could meaningfully contribute to future stories
- Define the unique character of this universe
- Provide creative constraints or opportunities

Be concise but thorough. Extract only what's truly significant."""

    try:
        response = await _call_openai(
            prompt=prompt,
            response_format="json",
            max_tokens=4000,
        )

        # Parse the JSON response
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_str)
                return result
            elif "{" in response:
                # Find the first { and last }
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
                result = json.loads(json_str)
                return result
            else:
                logger.error("Failed to parse JSON from LLM response")
                return {}

    except Exception as exc:
        logger.exception("Failed to extract universe elements with LLM: %s", exc)
        return {}


async def generate_universe_prompt_text(universe_prompt: UniversePrompt) -> str:
    """
    Generate a formatted prompt text from a universe prompt for use in story generation.

    This creates a well-structured prompt that can be injected into the LLM context
    with appropriate weighting based on the universe prompt settings.
    """
    sections = []

    # Characters section
    if universe_prompt.characters:
        char_lines = []
        for name, data in universe_prompt.characters.items():
            traits = ", ".join(data.get("traits", []))
            char_lines.append(f"- **{name}**: {data.get('description', '')} (Traits: {traits})")

        if char_lines:
            sections.append(f"**Characters** (weight: {universe_prompt.character_weight}):\n" + "\n".join(char_lines))

    # Settings section
    if universe_prompt.settings:
        setting_lines = []
        for name, data in universe_prompt.settings.items():
            setting_lines.append(f"- **{name}**: {data.get('description', '')}")
            if data.get("rules"):
                setting_lines.append(f"  Rules: {', '.join(data.get('rules', []))}")

        if setting_lines:
            sections.append(f"**Settings** (weight: {universe_prompt.setting_weight}):\n" + "\n".join(setting_lines))

    # Themes section
    if universe_prompt.themes:
        theme_lines = []
        for name, data in universe_prompt.themes.items():
            theme_lines.append(f"- **{name}**: {data.get('description', '')}")

        if theme_lines:
            sections.append(f"**Themes** (weight: {universe_prompt.theme_weight}):\n" + "\n".join(theme_lines))

    # Lore section
    if universe_prompt.lore:
        lore_lines = []
        for topic, data in universe_prompt.lore.items():
            lore_lines.append(f"- **{topic}**: {data.get('description', '')}")
            if data.get("facts"):
                for fact in data.get("facts", []):
                    lore_lines.append(f"  • {fact}")

        if lore_lines:
            sections.append(f"**Lore** (weight: {universe_prompt.lore_weight}):\n" + "\n".join(lore_lines))

    # Narrative constraints
    if universe_prompt.narrative_constraints:
        constraint_lines = [f"- {c}" for c in universe_prompt.narrative_constraints]
        sections.append("**Narrative Constraints**:\n" + "\n".join(constraint_lines))

    if not sections:
        return ""

    header = f"=== Universe Context: {universe_prompt.name} ===\n"
    if universe_prompt.description:
        header += f"{universe_prompt.description}\n\n"

    return header + "\n\n".join(sections)


__all__ = ["extract_universe_from_stories", "generate_universe_prompt_text"]
