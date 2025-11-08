from __future__ import annotations

import logging
from typing import Sequence

from sqlalchemy import select

from models import Chapter, Story
from story_generator import generate_story_cover_art, generate_story_summary

logger = logging.getLogger(__name__)


async def ensure_story_completion_assets(session, story: Story) -> None:
    """Populate summary and cover art for a completed story if missing."""

    needs_summary = not getattr(story, "summary", None)
    needs_cover = not getattr(story, "cover_art_url", None)

    if not (needs_summary or needs_cover):
        return

    chapters: Sequence[Chapter]
    if hasattr(story, "chapters") and story.chapters:
        chapters = list(story.chapters)
    else:
        stmt = select(Chapter).where(Chapter.story_id == story.id).order_by(Chapter.chapter_number)
        chapters = list((await session.execute(stmt)).scalars())

    updated = False
    summary = story.summary
    if needs_summary:
        summary = await generate_story_summary(story, chapters)
        if summary:
            story.summary = summary
            updated = True
        else:
            logger.warning("Failed to generate summary for story %s", story.id)

    if needs_cover and summary:
        cover_url = await generate_story_cover_art(story, summary)
        if cover_url:
            story.cover_art_url = cover_url
            updated = True
        else:
            logger.warning("Failed to generate cover art for story %s", story.id)

    if updated:
        await session.flush()


__all__ = ["ensure_story_completion_assets"]
