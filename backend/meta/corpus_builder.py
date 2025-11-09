from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Chapter, Story, StoryCorpus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StoryCorpusSnapshot:
    """Lightweight, serialisable representation of a story corpus."""

    story_id: uuid.UUID
    last_chapter_number: int
    word_count: int
    token_count: int
    updated_at: datetime
    data: dict

    @classmethod
    def from_model(cls, corpus: StoryCorpus) -> "StoryCorpusSnapshot":
        return cls(
            story_id=corpus.story_id,
            last_chapter_number=corpus.last_chapter_number,
            word_count=corpus.word_count,
            token_count=corpus.token_count,
            updated_at=corpus.updated_at,
            data=dict(corpus.data or {}),
        )


class CorpusExtractionService:
    """Builds and caches full-text corpora for downstream meta analysis."""

    def __init__(self, max_chapters: int | None = None) -> None:
        self.max_chapters = max_chapters

    async def refresh_story_corpora(
        self,
        session: AsyncSession,
        stories: Sequence[Story],
    ) -> dict[uuid.UUID, StoryCorpusSnapshot]:
        """Ensure story corpora are materialised and up to date.

        Returns a mapping of story_id to snapshots that can be fed into
        downstream processors.
        """

        if not stories:
            return {}

        story_ids = [story.id for story in stories]
        existing_rows = (
            await session.execute(
                select(StoryCorpus).where(StoryCorpus.story_id.in_(story_ids))
            )
        ).scalars()
        existing_map = {row.story_id: row for row in existing_rows}

        snapshots: dict[uuid.UUID, StoryCorpusSnapshot] = {}
        for story in stories:
            existing = existing_map.get(story.id)
            if await self._should_refresh(story, existing):
                snapshot = await self._build_snapshot(session, story)
                if existing is None:
                    session.add(
                        StoryCorpus(
                            story_id=story.id,
                            updated_at=snapshot.updated_at,
                            last_chapter_number=snapshot.last_chapter_number,
                            word_count=snapshot.word_count,
                            token_count=snapshot.token_count,
                            data=snapshot.data,
                        )
                    )
                else:
                    existing.updated_at = snapshot.updated_at
                    existing.last_chapter_number = snapshot.last_chapter_number
                    existing.word_count = snapshot.word_count
                    existing.token_count = snapshot.token_count
                    existing.data = snapshot.data
                logger.debug("Story corpus refreshed", extra={"story_id": str(story.id)})
            else:
                snapshot = StoryCorpusSnapshot.from_model(existing)  # type: ignore[arg-type]
            snapshots[story.id] = snapshot

        return snapshots

    async def _should_refresh(
        self,
        story: Story,
        corpus: StoryCorpus | None,
    ) -> bool:
        if corpus is None:
            return True
        if corpus.last_chapter_number != story.chapter_count:
            return True
        if story.last_chapter_at and corpus.updated_at < story.last_chapter_at:
            return True
        if corpus.word_count == 0:
            return True
        return False

    async def _build_snapshot(
        self,
        session: AsyncSession,
        story: Story,
    ) -> StoryCorpusSnapshot:
        chapters = await self._load_chapters(session, story)
        documents = []
        total_words = 0
        total_tokens = 0

        for chapter in chapters:
            words = self._estimate_words(chapter.content)
            tokens = chapter.tokens_used or words
            total_words += words
            total_tokens += tokens
            documents.append(
                {
                    "id": str(chapter.id),
                    "chapter_number": chapter.chapter_number,
                    "content": chapter.content,
                    "created_at": chapter.created_at.isoformat(),
                    "word_count": words,
                    "tokens_used": tokens,
                }
            )

        payload = {
            "story_id": str(story.id),
            "title": story.title,
            "premise": story.premise,
            "chapters": documents,
            "chapter_count": len(chapters),
            "style": {
                "tone": story.tone,
                "genre_tags": story.genre_tags,
                "style_authors": story.style_authors,
                "narrative_perspective": story.narrative_perspective,
            },
        }

        snapshot = StoryCorpusSnapshot(
            story_id=story.id,
            last_chapter_number=story.chapter_count,
            word_count=total_words,
            token_count=total_tokens,
            updated_at=datetime.utcnow(),
            data=payload,
        )
        return snapshot

    async def _load_chapters(
        self,
        session: AsyncSession,
        story: Story,
    ) -> Iterable[Chapter]:
        if getattr(story, "chapters", None):
            chapters = list(story.chapters)
        else:
            stmt = (
                select(Chapter)
                .where(Chapter.story_id == story.id)
                .order_by(Chapter.chapter_number)
            )
            chapters = list((await session.execute(stmt)).scalars())

        chapters.sort(key=lambda item: item.chapter_number)
        if self.max_chapters is not None:
            chapters = chapters[-self.max_chapters :]
        return chapters

    def _estimate_words(self, text: str) -> int:
        text = text or ""
        if not text:
            return 0
        # A very small guard to avoid zero when there is text
        return max(1, math.ceil(len(text.split())))
