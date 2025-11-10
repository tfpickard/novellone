from __future__ import annotations

import logging
import re
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Story, StoryEntity, StoryEntityOverride, StoryTheme
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


@dataclass(slots=True)
class EntityOverrideRules:
    suppress: set[str]
    merges: dict[str, str]


@dataclass(slots=True)
class EntityRefreshResult:
    processed: int
    entities: int
    themes: int
    started_at: datetime
    finished_at: datetime
    duration_ms: float

    def as_metadata(self) -> dict[str, int | float]:
        return {
            "processed": self.processed,
            "entities": self.entities,
            "themes": self.themes,
            "duration_ms": round(self.duration_ms, 2),
        }


def apply_overrides_to_entities(
    entities: Sequence[StoryEntity], rules: EntityOverrideRules | None
) -> list[StoryEntity]:
    if not rules:
        return list(entities)

    aggregated: dict[str, StoryEntity] = {}
    for entity in entities:
        name = entity.name
        if name in rules.suppress:
            continue

        target_name = rules.merges.get(name, name)
        alias_set = set(entity.aliases or [])
        if target_name != name:
            alias_set.update({name, target_name})
            entity.name = target_name

        key = entity.name.lower()
        existing = aggregated.get(key)
        if existing:
            existing.occurrence_count += entity.occurrence_count
            existing.confidence = max(existing.confidence or 0.0, entity.confidence or 0.0)

            if entity.first_seen_chapter is not None and (
                existing.first_seen_chapter is None
                or entity.first_seen_chapter < existing.first_seen_chapter
            ):
                existing.first_seen_chapter = entity.first_seen_chapter
            if entity.last_seen_chapter is not None and (
                existing.last_seen_chapter is None
                or entity.last_seen_chapter > existing.last_seen_chapter
            ):
                existing.last_seen_chapter = entity.last_seen_chapter

            existing_aliases = set(existing.aliases or [])
            existing_aliases.update(alias_set)
            if existing_aliases:
                existing.aliases = sorted(existing_aliases)

            existing_metadata = existing.metadata_json or {}
            entity_metadata = entity.metadata_json or {}
            existing_chapters = set(existing_metadata.get("supporting_chapters", []))
            entity_chapters = set(entity_metadata.get("supporting_chapters", []))
            combined = sorted(existing_chapters | entity_chapters)
            if combined:
                existing_metadata["supporting_chapters"] = combined
                existing.metadata_json = existing_metadata
        else:
            if alias_set:
                entity.aliases = sorted(alias_set)
            aggregated[key] = entity

    return sorted(aggregated.values(), key=lambda item: item.name.lower())


class EntityExtractionService:
    """Derives named entities and thematic motifs from story corpora."""

    def __init__(self, min_occurrences: int = 2) -> None:
        self.min_occurrences = min_occurrences

    async def refresh_entities(
        self,
        session: AsyncSession,
        stories: Sequence[Story],
        corpora: dict[uuid.UUID, StoryCorpusSnapshot],
    ) -> EntityRefreshResult:
        started_at = datetime.utcnow()
        timer = time.perf_counter()
        if not stories:
            finished_at = datetime.utcnow()
            duration_ms = (time.perf_counter() - timer) * 1000
            return EntityRefreshResult(
                processed=0,
                entities=0,
                themes=0,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )

        processed = 0
        total_entities = 0
        total_themes = 0

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

            overrides = await self._load_overrides(session, story.id)
            entities = apply_overrides_to_entities(entities, overrides)

            for entity in entities:
                session.add(entity)
            for theme in themes:
                session.add(theme)

            processed += 1
            total_entities += len(entities)
            total_themes += len(themes)

            logger.debug(
                "Entity extraction completed",
                extra={
                    "story_id": str(story.id),
                    "entities": len(entities),
                    "themes": len(themes),
                    "overrides": {
                        "suppressed": len(overrides.suppress) if overrides else 0,
                        "merged": len(overrides.merges) if overrides else 0,
                    },
                },
            )

        finished_at = datetime.utcnow()
        duration_ms = (time.perf_counter() - timer) * 1000
        return EntityRefreshResult(
            processed=processed,
            entities=total_entities,
            themes=total_themes,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
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
                    metadata_json={
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

        def add_theme(
            *,
            name: str,
            weight: float,
            confidence: float,
            source: str,
            rank: int,
            seen: set[str],
        ) -> None:
            normalised = name.strip()
            if not normalised:
                return
            truncated = normalised[:255]
            key = truncated.casefold()
            if key in seen:
                return
            seen.add(key)
            metadata: dict[str, object] = {"rank": rank}
            if len(normalised) > 255:
                metadata["original_name"] = normalised
            themes.append(
                StoryTheme(
                    story_id=story.id,
                    name=truncated,
                    weight=weight,
                    confidence=confidence,
                    source=source,
                    metadata_json=metadata,
                    updated_at=datetime.utcnow(),
                )
            )

        seen_themes: set[str] = set()

        base_themes = self._normalise_theme_json(story.theme_json)
        base_rank = 0
        for theme_name in base_themes:
            base_rank += 1
            add_theme(
                name=theme_name,
                weight=1.0,
                confidence=0.6,
                source="story.theme_json",
                rank=base_rank,
                seen=seen_themes,
            )

        keywords = self._extract_keywords(corpus)
        keyword_rank = 0
        for keyword in keywords:
            keyword_rank += 1
            add_theme(
                name=keyword,
                weight=max(0.3, 1.0 - 0.05 * (keyword_rank - 1)),
                confidence=0.45,
                source="keyword",
                rank=keyword_rank,
                seen=seen_themes,
            )

        return themes

    async def _load_overrides(
        self, session: AsyncSession, story_id: uuid.UUID
    ) -> EntityOverrideRules | None:
        rows = (
            await session.execute(
                select(StoryEntityOverride).where(
                    (StoryEntityOverride.story_id == story_id)
                    | (StoryEntityOverride.story_id.is_(None))
                )
            )
        ).scalars()
        suppress: set[str] = set()
        merges: dict[str, str] = {}
        for row in rows:
            action = (row.action or "").lower()
            if action == "suppress":
                suppress.add(row.name)
            elif action == "merge" and row.target_name:
                merges[row.name] = row.target_name

        if not suppress and not merges:
            return None
        return EntityOverrideRules(suppress=suppress, merges=merges)

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
