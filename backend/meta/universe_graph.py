from __future__ import annotations

import itertools
import logging
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Story,
    StoryEntity,
    StoryTheme,
    StoryUniverseLink,
    UniverseCluster,
    UniverseClusterMembership,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class UniverseRefreshResult:
    stories: int
    links: int
    clusters: int
    started_at: datetime
    finished_at: datetime
    duration_ms: float

    def as_metadata(self) -> dict[str, int | float]:
        return {
            "stories": self.stories,
            "links": self.links,
            "clusters": self.clusters,
            "duration_ms": round(self.duration_ms, 2),
        }


class UniverseGraphService:
    """Constructs an interconnected universe graph from extracted entities."""

    def __init__(self, min_weight: float = 0.5) -> None:
        self.min_weight = min_weight

    async def refresh_universe(self, session: AsyncSession) -> UniverseRefreshResult:
        started_at = datetime.utcnow()
        timer = time.perf_counter()
        stories = (
            await session.execute(select(Story.id, Story.title))
        ).all()
        if not stories:
            await self._clear_tables(session)
            finished_at = datetime.utcnow()
            duration_ms = (time.perf_counter() - timer) * 1000
            return UniverseRefreshResult(
                stories=0,
                links=0,
                clusters=0,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )

        story_titles = {row.id: row.title for row in stories}

        entities = list((await session.execute(select(StoryEntity))).scalars())
        themes = list((await session.execute(select(StoryTheme))).scalars())

        entity_map = defaultdict(list)
        for entity in entities:
            entity_map[entity.story_id].append(entity)

        theme_map = defaultdict(list)
        for theme in themes:
            theme_map[theme.story_id].append(theme)

        edges = self._build_edges(entity_map, theme_map)

        story_ids = {row.id for row in stories}

        link_count = await self._persist_links(session, edges)
        cluster_count = await self._persist_clusters(
            session,
            edges,
            entity_map,
            theme_map,
            story_titles,
            story_ids,
        )

        finished_at = datetime.utcnow()
        duration_ms = (time.perf_counter() - timer) * 1000
        return UniverseRefreshResult(
            stories=len(story_ids),
            links=link_count,
            clusters=cluster_count,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )

    def _build_edges(
        self,
        entity_map: dict[uuid.UUID, list[StoryEntity]],
        theme_map: dict[uuid.UUID, list[StoryTheme]],
    ) -> dict[tuple[uuid.UUID, uuid.UUID], dict]:
        story_ids = set(entity_map.keys()) | set(theme_map.keys())
        edges: dict[tuple[uuid.UUID, uuid.UUID], dict] = {}

        for left, right in itertools.combinations(sorted(story_ids, key=lambda value: str(value)), 2):
            left_entities = {entity.name for entity in entity_map.get(left, [])}
            right_entities = {entity.name for entity in entity_map.get(right, [])}
            shared_entities = sorted(left_entities & right_entities)

            left_themes = {theme.name.lower() for theme in theme_map.get(left, [])}
            right_themes = {theme.name.lower() for theme in theme_map.get(right, [])}
            shared_themes = sorted({theme.title() for theme in left_themes & right_themes})

            weight = len(shared_entities) * 1.0 + len(shared_themes) * 0.5
            if weight < self.min_weight:
                continue

            edges[(left, right)] = {
                "shared_entities": shared_entities,
                "shared_themes": shared_themes,
                "weight": weight,
            }

        return edges

    async def _persist_links(
        self,
        session: AsyncSession,
        edges: dict[tuple[uuid.UUID, uuid.UUID], dict],
    ) -> int:
        await session.execute(delete(StoryUniverseLink))
        now = datetime.utcnow()
        count = 0
        for (source, target), data in edges.items():
            session.add(
                StoryUniverseLink(
                    source_story_id=source,
                    target_story_id=target,
                    weight=data["weight"],
                    shared_entities=data.get("shared_entities"),
                    shared_themes=data.get("shared_themes"),
                    metadata_json={
                        "entity_count": len(data.get("shared_entities") or []),
                        "theme_count": len(data.get("shared_themes") or []),
                    },
                    updated_at=now,
                )
            )
            count += 1
        return count

    async def _persist_clusters(
        self,
        session: AsyncSession,
        edges: dict[tuple[uuid.UUID, uuid.UUID], dict],
        entity_map: dict[uuid.UUID, list[StoryEntity]],
        theme_map: dict[uuid.UUID, list[StoryTheme]],
        titles: dict[uuid.UUID, str],
        all_story_ids: set[uuid.UUID],
    ) -> int:
        await session.execute(delete(UniverseClusterMembership))
        await session.execute(delete(UniverseCluster))

        adjacency = self._build_adjacency(edges)
        for story_id in all_story_ids:
            adjacency.setdefault(story_id, {})
        clusters = list(self._connected_components(adjacency))

        now = datetime.utcnow()
        created = 0
        for index, nodes in enumerate(clusters, start=1):
            cluster_id = uuid.uuid4()
            cohesion = self._calculate_cohesion(nodes, adjacency)
            metadata = self._cluster_metadata(nodes, entity_map, theme_map, titles)

            session.add(
                UniverseCluster(
                    id=cluster_id,
                    label=f"Cluster {index}",
                    size=len(nodes),
                    cohesion=cohesion,
                    metadata_json=metadata,
                    updated_at=now,
                )
            )

            for story_id in nodes:
                weight = sum(adjacency[story_id].values()) / max(len(nodes) - 1, 1)
                session.add(
                    UniverseClusterMembership(
                        story_id=story_id,
                        cluster_id=cluster_id,
                        weight=weight,
                        metadata_json={
                            "related_stories": list(adjacency[story_id].keys())
                        },
                        updated_at=now,
                    )
                )

            created += 1

        return created

    async def _clear_tables(self, session: AsyncSession) -> None:
        await session.execute(delete(StoryUniverseLink))
        await session.execute(delete(UniverseClusterMembership))
        await session.execute(delete(UniverseCluster))

    def _build_adjacency(
        self,
        edges: dict[tuple[uuid.UUID, uuid.UUID], dict],
    ) -> dict[uuid.UUID, dict[uuid.UUID, float]]:
        adjacency: dict[uuid.UUID, dict[uuid.UUID, float]] = defaultdict(dict)
        for (left, right), data in edges.items():
            weight = float(data.get("weight") or 0.0)
            adjacency[left][right] = weight
            adjacency[right][left] = weight
        return adjacency

    def _connected_components(
        self,
        adjacency: dict[uuid.UUID, dict[uuid.UUID, float]],
    ) -> Iterable[set[uuid.UUID]]:
        seen: set[uuid.UUID] = set()
        for node in adjacency:
            if node in seen:
                continue
            stack = [node]
            component: set[uuid.UUID] = set()
            while stack:
                current = stack.pop()
                if current in seen:
                    continue
                seen.add(current)
                component.add(current)
                stack.extend(neighbour for neighbour in adjacency[current].keys() if neighbour not in seen)
            if component:
                yield component

    def _calculate_cohesion(
        self,
        nodes: set[uuid.UUID],
        adjacency: dict[uuid.UUID, dict[uuid.UUID, float]],
    ) -> float:
        if len(nodes) <= 1:
            return 0.0
        weights = []
        for left, right in itertools.combinations(sorted(nodes, key=lambda value: str(value)), 2):
            weights.append(adjacency.get(left, {}).get(right, 0.0))
        if not weights:
            return 0.0
        return sum(weights) / len(weights)

    def _cluster_metadata(
        self,
        nodes: set[uuid.UUID],
        entity_map: dict[uuid.UUID, list[StoryEntity]],
        theme_map: dict[uuid.UUID, list[StoryTheme]],
        titles: dict[uuid.UUID, str],
    ) -> dict:
        entity_counter: Counter[str] = Counter()
        theme_counter: Counter[str] = Counter()

        for story_id in nodes:
            for entity in entity_map.get(story_id, []):
                entity_counter[entity.name] += entity.occurrence_count
            for theme in theme_map.get(story_id, []):
                theme_counter[theme.name.lower()] += 1

        top_entities = [name for name, _ in entity_counter.most_common(5)]
        top_themes = [name.title() for name, _ in theme_counter.most_common(5)]
        return {
            "story_titles": [titles.get(story_id) for story_id in nodes],
            "top_entities": top_entities,
            "top_themes": top_themes,
        }
