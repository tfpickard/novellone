from __future__ import annotations

import logging
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Sequence

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import Story, StoryEntity, StoryTheme
from .corpus_builder import StoryCorpusSnapshot

logger = logging.getLogger(__name__)


ENTITY_PATTERN = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b")
ENTITY_STOPWORDS = {
    "The",
    "A",
    "An",
    "And",
    "But",
    "Or",
    "He",
    "She",
    "They",
    "His",
    "Her",
    "Its",
    "Their",
    "Chapter",
    "Story",
}


class EntityExtractionService:
    """Derives named entities and thematic motifs from story corpora."""

    def __init__(self, min_occurrences: int = 2) -> None:
        self.min_occurrences = min_occurrences

    async def refresh_entities(
        self,
        session: AsyncSession,
        stories: Sequence[Story],
        corpora: dict[uuid.UUID, StoryCorpusSnapshot],
    ) -> None:
        if not stories:
            return

        for story in stories:
            corpus = corpora.get(story.id)
            if corpus is None:
                logger.debug(
                    "Skipping entity extraction; corpus missing",
                    extra={"story_id": str(story.id)},
                )
                continue

            await session.execute(delete(StoryEntity).where(StoryEntity.story_id == story.id))
            await session.execute(delete(StoryTheme).where(StoryTheme.story_id == story.id))

            entities = self._extract_entities(corpus)
            themes = self._extract_themes(story, corpus)

            for entity in entities:
                session.add(entity)
            for theme in themes:
                session.add(theme)

            logger.debug(
                "Entity extraction completed",
                extra={
                    "story_id": str(story.id),
                    "entities": len(entities),
                    "themes": len(themes),
                },
            )

    def _extract_entities(self, corpus: StoryCorpusSnapshot) -> list[StoryEntity]:
        counts: Counter[str] = Counter()
        chapter_occurrences: defaultdict[str, list[int]] = defaultdict(list)

        for doc in corpus.data.get("chapters", []):
            content = doc.get("content") or ""
            chapter_number = int(doc.get("chapter_number") or 0)
            for match in ENTITY_PATTERN.findall(content):
                cleaned = match.strip()
                if not cleaned or cleaned in ENTITY_STOPWORDS:
                    continue
                if cleaned.upper() == cleaned:
                    continue  # Skip SHOUTING identifiers
                counts[cleaned] += 1
                chapter_occurrences[cleaned].append(chapter_number)

        entities: list[StoryEntity] = []
        for name, occurrences in counts.items():
            if occurrences < self.min_occurrences:
                continue

            chapters = sorted(chapter_occurrences[name])
            first_seen = chapters[0] if chapters else None
            last_seen = chapters[-1] if chapters else None
            entity_type = "organization" if " " in name and name.split()[0].isupper() else "character"
            confidence = min(1.0, 0.3 + occurrences / 5)

            entities.append(
                StoryEntity(
                    story_id=corpus.story_id,
                    name=name,
                    entity_type=entity_type,
                    aliases=None,
                    confidence=confidence,
                    first_seen_chapter=first_seen,
                    last_seen_chapter=last_seen,
                    occurrence_count=occurrences,
                    metadata={
                        "supporting_chapters": chapters,
                    },
                    updated_at=datetime.utcnow(),
                )
            )

        return entities

    def _extract_themes(
        self,
        story: Story,
        corpus: StoryCorpusSnapshot,
    ) -> list[StoryTheme]:
        themes: list[StoryTheme] = []

        base_themes = self._normalise_theme_json(story.theme_json)
        for idx, theme_name in enumerate(base_themes, start=1):
            themes.append(
                StoryTheme(
                    story_id=story.id,
                    name=theme_name,
                    weight=1.0,
                    confidence=0.6,
                    source="story.theme_json",
                    metadata={"rank": idx},
                    updated_at=datetime.utcnow(),
                )
            )

        keywords = self._extract_keywords(corpus)
        for idx, keyword in enumerate(keywords, start=1):
            themes.append(
                StoryTheme(
                    story_id=story.id,
                    name=keyword,
                    weight=max(0.3, 1.0 - 0.05 * (idx - 1)),
                    confidence=0.45,
                    source="keyword",
                    metadata={"rank": idx},
                    updated_at=datetime.utcnow(),
                )
            )

        return themes

    def _normalise_theme_json(self, theme_json: object) -> list[str]:
        if not theme_json:
            return []
        if isinstance(theme_json, list):
            return [str(item).strip() for item in theme_json if str(item).strip()]
        if isinstance(theme_json, dict):
            values: list[str] = []
            for key, value in theme_json.items():
                key_str = str(key).strip()
                if key_str:
                    values.append(key_str)
                if isinstance(value, (list, tuple, set)):
                    values.extend(str(item).strip() for item in value if str(item).strip())
                elif isinstance(value, str):
                    stripped = value.strip()
                    if stripped:
                        values.append(stripped)
            return [item for item in values if item]
        return [str(theme_json).strip()]

    def _extract_keywords(self, corpus: StoryCorpusSnapshot) -> list[str]:
        text_blobs: list[str] = []
        text_blobs.append(corpus.data.get("premise") or "")
        for doc in corpus.data.get("chapters", []):
            text_blobs.append(doc.get("content") or "")

        combined = " ".join(text_blobs)
        tokens = [token.lower() for token in re.findall(r"[a-zA-Z]{5,}", combined)]
        counter = Counter(tokens)
        common = [word for word, count in counter.most_common(10) if count > 1]
        # Prefer distinct words to avoid overwhelming theme list
        unique: list[str] = []
        for word in common:
            if word not in unique:
                unique.append(word)
        return [word.title() for word in unique[:5]]
