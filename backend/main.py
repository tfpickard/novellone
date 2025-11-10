from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import selectinload

from auth import AdminSession, require_admin, router as auth_router
from background_worker import worker
from config import get_settings
from config_store import apply_config_updates, get_runtime_config
from logging_config import configure_logging
from database import get_session
from models import (
    Chapter,
    MetaAnalysisRun,
    Story,
    StoryEntity,
    StoryEntityOverride,
    StoryEvaluation,
    StoryTheme,
    StoryUniverseLink,
    SystemConfig,
    UniverseCluster,
    UniverseClusterMembership,
)
from story_generator import (
    generate_cover_image,
    get_hurllol_banner,
    get_premise_prompt_state,
    spawn_new_story,
    update_premise_prompt_state,
)
from text_stats import calculate_text_stats, calculate_aggregate_stats
from websocket_manager import ws_manager

settings = get_settings()
configure_logging(settings)

logger = logging.getLogger(__name__)

app = FastAPI(title="Hurl Unmasks Recursive Literature Leaking Out Light", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db_session():
    async with get_session() as session:
        yield session


app.include_router(auth_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Railway and monitoring."""
    return {"status": "healthy", "service": "hurl-unmasks-recursive-literature-leaking-out-light-backend"}


SessionDep = Annotated[Any, Depends(get_db_session)]
class ChapterRead(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID
    chapter_number: int
    content: str
    created_at: datetime
    tokens_used: int | None = None
    generation_time_ms: int | None = None
    model_used: str | None = None
    absurdity: float | None = None
    surrealism: float | None = None
    ridiculousness: float | None = None
    insanity: float | None = None
    stats: dict[str, Any] | None = None

    @classmethod
    def from_model(cls, chapter: Chapter, include_stats: bool = True) -> "ChapterRead":
        stats = calculate_text_stats(chapter.content) if include_stats else None
        return cls(
            id=chapter.id,
            story_id=chapter.story_id,
            chapter_number=chapter.chapter_number,
            content=chapter.content,
            created_at=chapter.created_at,
            tokens_used=chapter.tokens_used,
            generation_time_ms=chapter.generation_time_ms,
            model_used=chapter.model_used,
            absurdity=chapter.absurdity,
            surrealism=chapter.surrealism,
            ridiculousness=chapter.ridiculousness,
            insanity=chapter.insanity,
            stats=stats,
        )


class StoryEvaluationRead(BaseModel):
    id: uuid.UUID
    chapter_number: int
    overall_score: float
    coherence_score: float
    novelty_score: float
    engagement_score: float
    pacing_score: float
    should_continue: bool
    reasoning: str | None
    issues: list[str] | None
    evaluated_at: datetime

    @classmethod
    def from_model(cls, evaluation: StoryEvaluation) -> "StoryEvaluationRead":
        return cls(
            id=evaluation.id,
            chapter_number=evaluation.chapter_number,
            overall_score=evaluation.overall_score,
            coherence_score=evaluation.coherence_score,
            novelty_score=evaluation.novelty_score,
            engagement_score=evaluation.engagement_score,
            pacing_score=evaluation.pacing_score,
            should_continue=evaluation.should_continue,
            reasoning=evaluation.reasoning,
            issues=evaluation.issues or [],
            evaluated_at=evaluation.evaluated_at,
        )


class StoryRelatedItem(BaseModel):
    story_id: uuid.UUID
    title: str
    weight: float
    shared_entities: list[str] = Field(default_factory=list)
    shared_themes: list[str] = Field(default_factory=list)


class StoryUniverseContext(BaseModel):
    cluster_id: uuid.UUID | None = None
    cluster_label: str | None = None
    cluster_size: int = 0
    cohesion: float | None = None
    related_stories: list[StoryRelatedItem] = Field(default_factory=list)


class UniverseClusterSummary(BaseModel):
    cluster_id: uuid.UUID
    label: str | None
    size: int
    cohesion: float
    top_entities: list[str] = Field(default_factory=list)
    top_themes: list[str] = Field(default_factory=list)


class EntityAggregate(BaseModel):
    name: str
    story_count: int
    total_occurrences: int


class ThemeAggregate(BaseModel):
    name: str
    story_count: int


class MetaAnalysisRunRead(BaseModel):
    id: uuid.UUID
    run_type: str
    status: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    processed_items: int
    metadata: dict[str, Any] | None = None
    error_message: str | None = None

    @classmethod
    def from_model(cls, run: MetaAnalysisRun) -> "MetaAnalysisRunRead":
        return cls(
            id=run.id,
            run_type=run.run_type,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_ms=float(run.duration_ms or 0.0),
            processed_items=int(run.processed_items or 0),
            metadata=run.metadata_json or {},
            error_message=run.error_message,
        )


class EntityOverrideRead(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID | None
    name: str
    action: str
    target_name: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    scope: Literal["story", "global"]

    @classmethod
    def from_model(cls, override: StoryEntityOverride) -> "EntityOverrideRead":
        scope = "story" if override.story_id else "global"
        return cls(
            id=override.id,
            story_id=override.story_id,
            name=override.name,
            action=override.action,
            target_name=override.target_name,
            notes=override.notes,
            created_at=override.created_at,
            updated_at=override.updated_at,
            scope=scope,
        )


class EntityOverrideCreate(BaseModel):
    story_id: uuid.UUID | None = None
    name: str
    action: Literal["suppress", "merge"]
    target_name: str | None = None
    notes: str | None = None

    @field_validator("target_name")
    @classmethod
    def validate_target(cls, value: str | None, info: Any) -> str | None:
        action = info.data.get("action")
        if action == "merge" and not value:
            raise ValueError("target_name is required when action is 'merge'")
        return value


class EntityOverrideUpdate(BaseModel):
    name: str | None = None
    action: Literal["suppress", "merge"] | None = None
    target_name: str | None = None
    notes: str | None = None


class MetaRefreshRequest(BaseModel):
    story_id: uuid.UUID | None = None
    full_rebuild: bool = False


class MetricStoryResult(BaseModel):
    story_id: uuid.UUID
    title: str
    status: str
    cover_image_url: str | None
    chapter_count: int
    completed_at: datetime | None
    value: float


class MetricExtremes(BaseModel):
    key: str
    label: str
    description: str | None = None
    group: str
    order: int
    unit: str | None = None
    decimals: int = 2
    higher_is_better: bool = True
    best: MetricStoryResult | None = None
    worst: MetricStoryResult | None = None


class StorySummary(BaseModel):
    id: uuid.UUID
    title: str
    premise: str
    status: str
    created_at: datetime
    completed_at: datetime | None
    chapter_count: int
    total_tokens: int | None
    theme_json: dict[str, Any] | None
    cover_image_url: str | None
    style_authors: list[str] | None = None
    narrative_perspective: str | None = None
    tone: str | None = None
    genre_tags: list[str] | None = None
    estimated_reading_time_minutes: int | None = None
    absurdity_initial: float = 0.1
    surrealism_initial: float = 0.1
    ridiculousness_initial: float = 0.1
    insanity_initial: float = 0.1
    absurdity_increment: float = 0.05
    surrealism_increment: float = 0.05
    ridiculousness_increment: float = 0.05
    insanity_increment: float = 0.05
    aggregate_stats: dict[str, Any] | None = None
    universe: StoryUniverseContext | None = None

    @classmethod
    def from_model(
        cls,
        story: Story,
        include_stats: bool = False,
        universe: StoryUniverseContext | None = None,
    ) -> "StorySummary":
        aggregate_stats = None
        estimated_reading_time = None
        if include_stats and story.chapters:
            # Calculate aggregate statistics from all chapters
            chapters_data = [{"content": c.content} for c in story.chapters]
            aggregate_stats = calculate_aggregate_stats(chapters_data)
            # Estimate reading time at ~250 words per minute
            total_words = aggregate_stats.get("total_words", 0)
            if total_words > 0:
                estimated_reading_time = max(1, round(total_words / 250))

        return cls(
            id=story.id,
            title=story.title,
            premise=story.premise,
            status=story.status,
            created_at=story.created_at,
            completed_at=story.completed_at,
            chapter_count=story.chapter_count,
            total_tokens=story.total_tokens,
            theme_json=story.theme_json,
            cover_image_url=story.cover_image_url,
            style_authors=story.style_authors,
            narrative_perspective=story.narrative_perspective,
            tone=story.tone,
            genre_tags=story.genre_tags,
            estimated_reading_time_minutes=estimated_reading_time,
            absurdity_initial=story.absurdity_initial,
            surrealism_initial=story.surrealism_initial,
            ridiculousness_initial=story.ridiculousness_initial,
            insanity_initial=story.insanity_initial,
            absurdity_increment=story.absurdity_increment,
            surrealism_increment=story.surrealism_increment,
            ridiculousness_increment=story.ridiculousness_increment,
            insanity_increment=story.insanity_increment,
            aggregate_stats=aggregate_stats,
            universe=universe,
        )


class StoryDetail(StorySummary):
    completion_reason: str | None
    evaluations: list[StoryEvaluationRead]
    chapters: list[ChapterRead]
    entity_overrides: list[EntityOverrideRead] = Field(default_factory=list)

    @classmethod
    def from_model(
        cls,
        story: Story,
        universe: StoryUniverseContext | None = None,
        overrides: list[StoryEntityOverride] | None = None,
    ) -> "StoryDetail":
        override_payload = (
            [EntityOverrideRead.from_model(override) for override in overrides]
            if overrides
            else []
        )
        return cls(
            **StorySummary.from_model(story, include_stats=True, universe=universe).model_dump(),
            completion_reason=story.completion_reason,
            evaluations=[StoryEvaluationRead.from_model(e) for e in story.evaluations],
            chapters=[ChapterRead.from_model(c, include_stats=True) for c in story.chapters],
            entity_overrides=override_payload,
        )


class StoryCreate(BaseModel):
    title: str
    premise: str
    theme_json: dict[str, Any] | None = Field(default=None)


class StoryKillRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


@app.on_event("startup")
async def startup_event() -> None:
    await worker.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await worker.shutdown()


class ConfigUpdate(BaseModel):
    chapter_interval_seconds: Annotated[int | None, Field(default=None, ge=10, le=3600)] = None
    evaluation_interval_chapters: Annotated[int | None, Field(default=None, ge=1, le=50)] = None
    quality_score_min: Annotated[float | None, Field(default=None, ge=0.0, le=1.0)] = None
    max_chapters_per_story: Annotated[int | None, Field(default=None, ge=1, le=500)] = None
    min_active_stories: Annotated[int | None, Field(default=None, ge=0, le=100)] = None
    max_active_stories: Annotated[int | None, Field(default=None, ge=1, le=200)] = None
    context_window_chapters: Annotated[int | None, Field(default=None, ge=1, le=50)] = None
    openai_model: Annotated[str | None, Field(default=None, min_length=1, max_length=128)] = None
    openai_premise_model: Annotated[str | None, Field(default=None, min_length=1, max_length=128)] = None
    openai_eval_model: Annotated[str | None, Field(default=None, min_length=1, max_length=128)] = None
    openai_temperature_chapter: Annotated[float | None, Field(default=None, ge=0.0, le=2.0)] = None
    openai_temperature_premise: Annotated[float | None, Field(default=None, ge=0.0, le=2.0)] = None
    openai_temperature_eval: Annotated[float | None, Field(default=None, ge=0.0, le=2.0)] = None
    premise_prompt_refresh_interval: Annotated[int | None, Field(default=None, ge=1, le=200)] = None
    premise_prompt_stats_window: Annotated[int | None, Field(default=None, ge=1, le=200)] = None
    premise_prompt_variation_strength: Annotated[
        float | None, Field(default=None, ge=0.0, le=1.0)
    ] = None
    chaos_initial_min: Annotated[float | None, Field(default=None, ge=0.0, le=1.0)] = None
    chaos_initial_max: Annotated[float | None, Field(default=None, ge=0.0, le=1.0)] = None
    chaos_increment_min: Annotated[float | None, Field(default=None, ge=0.0, le=1.0)] = None
    chaos_increment_max: Annotated[float | None, Field(default=None, ge=0.0, le=1.0)] = None


class PromptUpdate(BaseModel):
    directives: list[str] | None = None
    rationale: str | None = None


def _format_prompt_state(state: dict[str, Any]) -> dict[str, Any]:
    raw_directives = state.get("directives") or []
    directives = [str(item).strip() for item in raw_directives if str(item).strip()]
    raw_components = state.get("hurllol_title_components") or []
    components = [str(component).strip() for component in raw_components if str(component).strip()]
    return {
        "directives": directives,
        "rationale": state.get("rationale"),
        "generated_at": state.get("generated_at"),
        "variation_strength": state.get("variation_strength"),
        "manual_override": bool(state.get("manual_override")),
        "stats_snapshot": state.get("stats_snapshot"),
        "hurllol_title": state.get("hurllol_title"),
        "hurllol_title_components": components,
        "hurllol_title_generated_at": state.get("hurllol_title_generated_at"),
    }


@app.get("/api/config")
async def get_public_config(
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    runtime = await get_runtime_config(session)
    return runtime.as_dict()


@app.patch("/api/config")
async def update_public_config(
    payload: ConfigUpdate,
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    try:
        runtime = await apply_config_updates(session, data)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await session.commit()
    return runtime.as_dict()


@app.get("/api/prompts")
async def get_prompt_state(
    session: SessionDep, _: AdminSession = Depends(require_admin)
) -> dict[str, Any]:
    state = await get_premise_prompt_state(session)
    await session.commit()
    return {"premise": _format_prompt_state(state)}


@app.patch("/api/prompts")
async def patch_prompt_state(
    payload: PromptUpdate,
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    state = await update_premise_prompt_state(
        session,
        directives=payload.directives,
        rationale=payload.rationale,
    )
    await session.commit()
    return {"premise": _format_prompt_state(state)}


@app.get("/api/hurllol")
async def get_hurllol_title(session: SessionDep) -> dict[str, Any]:
    banner = await get_hurllol_banner(session)
    await session.commit()
    return {
        "title": banner.get("title"),
        "components": banner.get("components", []),
        "generated_at": banner.get("generated_at"),
    }


@app.get("/api/stories")
async def list_stories(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    stmt = select(Story).order_by(Story.created_at.desc())
    count_stmt = select(func.count()).select_from(Story)
    if status:
        stmt = stmt.where(Story.status == status)
        count_stmt = count_stmt.where(Story.status == status)
    total = (await session.execute(count_stmt)).scalar_one()
    stories = (
        (await session.execute(stmt.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [StorySummary.from_model(story).model_dump() for story in stories],
    }


@app.get("/api/stories/{story_id}")
async def get_story(story_id: uuid.UUID, session: SessionDep) -> dict[str, Any]:
    stmt = (
        select(Story)
        .where(Story.id == story_id)
        .options(
            selectinload(Story.chapters),
            selectinload(Story.evaluations),
        )
    )
    result = await session.execute(stmt)
    story = result.scalars().first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    universe_context = await _get_story_universe_context(session, story.id)
    overrides = await _get_story_entity_overrides(session, story.id)
    return StoryDetail.from_model(
        story, universe=universe_context, overrides=overrides
    ).model_dump()


async def _get_story_universe_context(
    session: Any,
    story_id: uuid.UUID,
) -> StoryUniverseContext | None:
    membership_stmt = (
        select(UniverseClusterMembership, UniverseCluster)
        .join(UniverseCluster, UniverseClusterMembership.cluster_id == UniverseCluster.id)
        .where(UniverseClusterMembership.story_id == story_id)
    )
    membership_row = (await session.execute(membership_stmt)).first()

    cluster_id: uuid.UUID | None = None
    cluster_label: str | None = None
    cluster_size = 0
    cohesion: float | None = None

    if membership_row:
        _membership, cluster = membership_row
        cluster_id = cluster.id
        cluster_label = cluster.label
        cluster_size = cluster.size
        cohesion = cluster.cohesion

    links_stmt = select(StoryUniverseLink).where(
        (StoryUniverseLink.source_story_id == story_id)
        | (StoryUniverseLink.target_story_id == story_id)
    )
    links = list((await session.execute(links_stmt)).scalars())

    related_ids = {
        link.target_story_id if link.source_story_id == story_id else link.source_story_id
        for link in links
    }

    titles: dict[uuid.UUID, str] = {}
    if related_ids:
        title_rows = (
            await session.execute(
                select(Story.id, Story.title).where(Story.id.in_(related_ids))
            )
        ).all()
        titles = {row.id: row.title for row in title_rows}

    related_items: list[StoryRelatedItem] = []
    for link in links:
        other_story_id = (
            link.target_story_id
            if link.source_story_id == story_id
            else link.source_story_id
        )
        related_items.append(
            StoryRelatedItem(
                story_id=other_story_id,
                title=titles.get(other_story_id, ""),
                weight=link.weight,
                shared_entities=link.shared_entities or [],
                shared_themes=link.shared_themes or [],
            )
        )

    if not cluster_id and not related_items:
        return StoryUniverseContext()

    related_items.sort(key=lambda item: item.weight, reverse=True)
    return StoryUniverseContext(
        cluster_id=cluster_id,
        cluster_label=cluster_label,
        cluster_size=cluster_size,
        cohesion=cohesion,
        related_stories=related_items,
    )


async def _get_story_entity_overrides(
    session: Any, story_id: uuid.UUID
) -> list[StoryEntityOverride]:
    stmt = (
        select(StoryEntityOverride)
        .where(
            (StoryEntityOverride.story_id == story_id)
            | (StoryEntityOverride.story_id.is_(None))
        )
        .order_by(StoryEntityOverride.created_at.asc())
    )
    return list((await session.execute(stmt)).scalars())


@app.get("/api/stories/{story_id}/theme")
async def get_story_theme(story_id: uuid.UUID, session: SessionDep) -> dict[str, Any]:
    stmt = select(Story.theme_json).where(Story.id == story_id)
    result = await session.execute(stmt)
    theme = result.scalar_one_or_none()
    if theme is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return theme


@app.post("/api/stories/{story_id}/kill")
async def kill_story(
    story_id: uuid.UUID,
    payload: StoryKillRequest,
    session: SessionDep,
) -> dict[str, Any]:
    stmt = select(Story).where(Story.id == story_id)
    story = (await session.execute(stmt)).scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    reason = (payload.reason or "Terminated manually").strip() or "Terminated manually"
    if story.status != "completed":
        story.status = "completed"
        story.completed_at = datetime.utcnow()
        story.completion_reason = reason
        
        # Generate cover image for the completed story (only if we don't have one)
        if not story.cover_image_url:
            logger.info("Generating cover image for manually killed story: %s", story.title)
            try:
                cover_url = await generate_cover_image(story.title, story.premise)
                if cover_url:
                    story.cover_image_url = cover_url
                    logger.info("✓ Cover image saved for manually killed story %s", story.title)
                else:
                    logger.warning("✗ No cover image URL returned for story %s", story.title)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to generate cover image for story %s: %s", story.title, exc)
        else:
            logger.debug("Story %s already has cover image, skipping generation", story.title)
        
        await session.commit()

        if settings.enable_websocket:
            await ws_manager.broadcast(
                {
                    "type": "story_completed",
                    "story_id": str(story.id),
                    "reason": reason,
                    "cover_image_url": story.cover_image_url,
                }
            )
        logger.info("Story %s killed manually: %s", story.title, reason)
    else:
        if story.completion_reason != reason:
            story.completion_reason = reason
            await session.commit()
        logger.info("Kill requested for already completed story %s", story.title)

    return await get_story(story_id, session)


@app.post("/api/stories/{story_id}/generate", status_code=201)
async def generate_chapter_now(story_id: uuid.UUID, session: SessionDep) -> dict[str, Any]:
    stmt = (
        select(Story)
        .where(Story.id == story_id)
        .options(selectinload(Story.chapters), selectinload(Story.evaluations))
    )
    story = (await session.execute(stmt)).scalars().first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status != "active":
        raise HTTPException(status_code=400, detail="Only active stories can generate new chapters")

    runtime_config = await get_runtime_config(session)
    if story.chapter_count >= runtime_config.max_chapters_per_story:
        raise HTTPException(status_code=400, detail="Story already reached the maximum chapter count")

    await worker.generate_chapter_manual(session, story, runtime_config)

    await session.commit()

    refreshed = (await session.execute(stmt)).scalars().first()
    if not refreshed:
        raise HTTPException(status_code=404, detail="Story not found after generation")

    logger.info("Manual chapter generation requested for story %s", refreshed.title)
    universe_context = await _get_story_universe_context(session, refreshed.id)
    overrides = await _get_story_entity_overrides(session, refreshed.id)
    return StoryDetail.from_model(
        refreshed, universe=universe_context, overrides=overrides
    ).model_dump()


@app.post("/api/stories", status_code=201)
async def create_story(payload: StoryCreate, session: SessionDep) -> dict[str, Any]:
    story = Story(
        title=payload.title,
        premise=payload.premise,
        theme_json=payload.theme_json,
        status="active",
    )
    session.add(story)
    await session.flush()
    stmt = (
        select(Story)
        .where(Story.id == story.id)
        .options(selectinload(Story.chapters), selectinload(Story.evaluations))
    )
    story_obj = (await session.execute(stmt)).scalars().first()
    if not story_obj:
        raise HTTPException(status_code=500, detail="Failed to load created story")
    universe_context = await _get_story_universe_context(session, story_obj.id)
    overrides = await _get_story_entity_overrides(session, story_obj.id)
    return StoryDetail.from_model(
        story_obj, universe=universe_context, overrides=overrides
    ).model_dump()


@app.get("/api/universe/overview")
async def get_universe_overview(session: SessionDep) -> dict[str, Any]:
    cluster_rows = list((await session.execute(select(UniverseCluster))).scalars())
    clusters = [
        UniverseClusterSummary(
            cluster_id=row.id,
            label=row.label,
            size=row.size,
            cohesion=row.cohesion,
            top_entities=(row.metadata_json or {}).get("top_entities", []),
            top_themes=(row.metadata_json or {}).get("top_themes", []),
        ).model_dump()
        for row in cluster_rows
    ]

    entity_rows = (
        await session.execute(
            select(
                StoryEntity.name,
                func.count(StoryEntity.story_id).label("story_count"),
                func.sum(StoryEntity.occurrence_count).label("occurrences"),
            )
            .group_by(StoryEntity.name)
            .order_by(func.sum(StoryEntity.occurrence_count).desc())
            .limit(10)
        )
    ).all()
    top_entities = [
        EntityAggregate(
            name=row.name,
            story_count=int(row.story_count or 0),
            total_occurrences=int(row.occurrences or 0),
        ).model_dump()
        for row in entity_rows
    ]

    theme_rows = (
        await session.execute(
            select(
                StoryTheme.name,
                func.count(StoryTheme.story_id).label("story_count"),
            )
            .group_by(StoryTheme.name)
            .order_by(func.count(StoryTheme.story_id).desc())
            .limit(10)
        )
    ).all()
    top_themes = [
        ThemeAggregate(
            name=row.name,
            story_count=int(row.story_count or 0),
        ).model_dump()
        for row in theme_rows
    ]

    return {
        "clusters": clusters,
        "top_entities": top_entities,
        "top_themes": top_themes,
    }


@app.get("/api/universe/metrics")
async def get_universe_metrics(
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    runs = (
        await session.execute(
            select(MetaAnalysisRun).order_by(MetaAnalysisRun.started_at.desc()).limit(50)
        )
    ).scalars().all()
    run_payload = [MetaAnalysisRunRead.from_model(run).model_dump() for run in runs]

    grouped: dict[str, list[MetaAnalysisRun]] = {}
    for run in runs:
        grouped.setdefault(run.run_type, []).append(run)

    summary: dict[str, dict[str, Any]] = {}
    for run_type, entries in grouped.items():
        durations = [float(entry.duration_ms or 0.0) for entry in entries]
        successes = sum(1 for entry in entries if entry.status == "success")
        summary[run_type] = {
            "total_runs": len(entries),
            "success_rate": successes / len(entries) if entries else 0.0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0,
            "latest_status": entries[0].status,
            "latest_finished_at": entries[0].finished_at.isoformat(),
        }

    runtime = {
        "last_universe_refresh": worker._last_universe_refresh.isoformat()  # type: ignore[attr-defined]
        if worker._last_universe_refresh
        else None,
        "last_full_refresh": worker._last_full_refresh.isoformat()  # type: ignore[attr-defined]
        if worker._last_full_refresh
        else None,
    }

    return {"runs": run_payload, "summary": summary, "runtime": runtime}


@app.get("/api/universe/overrides")
async def list_entity_overrides(
    session: SessionDep,
    story_id: uuid.UUID | None = Query(default=None),
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(StoryEntityOverride)
    if story_id:
        stmt = stmt.where(
            (StoryEntityOverride.story_id == story_id)
            | (StoryEntityOverride.story_id.is_(None))
        )
    stmt = stmt.order_by(StoryEntityOverride.created_at.asc())
    overrides = list((await session.execute(stmt)).scalars())
    return {
        "overrides": [EntityOverrideRead.from_model(row).model_dump() for row in overrides]
    }


@app.post("/api/universe/overrides", status_code=201)
async def create_entity_override(
    payload: EntityOverrideCreate,
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    override = StoryEntityOverride(
        story_id=payload.story_id,
        name=payload.name,
        action=payload.action,
        target_name=payload.target_name,
        notes=payload.notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(override)
    await session.flush()
    await session.commit()
    worker.request_meta_refresh(
        override.story_id, full_rebuild=override.story_id is None
    )
    await session.refresh(override)
    return EntityOverrideRead.from_model(override).model_dump()


@app.patch("/api/universe/overrides/{override_id}")
async def update_entity_override(
    override_id: uuid.UUID,
    payload: EntityOverrideUpdate,
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    override = await session.get(StoryEntityOverride, override_id)
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")

    updates = payload.model_dump(exclude_none=True)
    if updates.get("action") == "merge" and not (
        updates.get("target_name") or override.target_name
    ):
        raise HTTPException(
            status_code=422,
            detail="target_name is required when setting action to 'merge'",
        )

    for key, value in updates.items():
        setattr(override, key, value)
    override.updated_at = datetime.utcnow()
    await session.commit()
    worker.request_meta_refresh(
        override.story_id, full_rebuild=override.story_id is None
    )
    await session.refresh(override)
    return EntityOverrideRead.from_model(override).model_dump()


@app.delete("/api/universe/overrides/{override_id}")
async def delete_entity_override(
    override_id: uuid.UUID,
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    override = await session.get(StoryEntityOverride, override_id)
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")

    story_id = override.story_id
    await session.delete(override)
    await session.commit()
    worker.request_meta_refresh(story_id, full_rebuild=story_id is None)
    return {"status": "deleted"}


@app.post("/api/universe/refresh", status_code=202)
async def queue_meta_refresh(
    payload: MetaRefreshRequest,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    story_id = payload.story_id
    worker.request_meta_refresh(
        story_id,
        full_rebuild=payload.full_rebuild or story_id is None,
    )
    scope = "story" if story_id else "full"
    return {"status": "queued", "scope": scope}


@app.get("/api/stats")
async def get_stats(session: SessionDep) -> dict[str, Any]:
    total_stories = (
        await session.execute(select(func.count()).select_from(Story))
    ).scalar_one()
    total_chapters = (
        await session.execute(select(func.count()).select_from(Chapter))
    ).scalar_one()
    active_stories = (
        await session.execute(
            select(func.count()).select_from(Story).where(Story.status == "active")
        )
    ).scalar_one()
    completed_stories = (
        await session.execute(
            select(func.count()).select_from(Story).where(Story.status == "completed")
        )
    ).scalar_one()
    average_chapters = 0.0
    if total_stories:
        chapter_counts = (
            await session.execute(select(func.avg(Story.chapter_count)))
        ).scalar_one()
        average_chapters = float(chapter_counts or 0.0)
    token_usage = (
        await session.execute(select(func.sum(Story.total_tokens)))
    ).scalar_one()
    recent_activity = (
        (
            await session.execute(
                select(Chapter).order_by(Chapter.created_at.desc()).limit(10)
            )
        )
        .scalars()
        .all()
    )
    
    # Calculate average chaos parameters
    avg_absurdity = (
        await session.execute(select(func.avg(Chapter.absurdity)))
    ).scalar_one() or 0.0
    avg_surrealism = (
        await session.execute(select(func.avg(Chapter.surrealism)))
    ).scalar_one() or 0.0
    avg_ridiculousness = (
        await session.execute(select(func.avg(Chapter.ridiculousness)))
    ).scalar_one() or 0.0
    avg_insanity = (
        await session.execute(select(func.avg(Chapter.insanity)))
    ).scalar_one() or 0.0
    
    # Calculate aggregate text statistics across all chapters
    all_chapters = (
        await session.execute(select(Chapter))
    ).scalars().all()
    
    aggregate_text_stats = None
    if all_chapters:
        chapters_data = [{"content": c.content} for c in all_chapters]
        aggregate_text_stats = calculate_aggregate_stats(chapters_data)
    
    return {
        "total_stories": total_stories,
        "total_chapters": total_chapters,
        "active_stories": active_stories,
        "completed_stories": completed_stories,
        "average_chapters_per_story": average_chapters,
        "total_tokens_used": token_usage or 0,
        "average_absurdity": float(avg_absurdity),
        "average_surrealism": float(avg_surrealism),
        "average_ridiculousness": float(avg_ridiculousness),
        "average_insanity": float(avg_insanity),
        "text_statistics": aggregate_text_stats or {},
        "recent_activity": [
            ChapterRead.from_model(c, include_stats=False).model_dump() for c in recent_activity
        ],
    }


@app.get("/api/recommendations")
async def get_story_recommendations(session: SessionDep) -> dict[str, Any]:
    story_rows = (await session.execute(select(Story))).scalars().all()
    if not story_rows:
        return {"metrics": []}

    stories: dict[uuid.UUID, Story] = {story.id: story for story in story_rows}
    aggregates: dict[uuid.UUID, dict[str, float]] = {
        story_id: {
            "chapter_count": float(story.chapter_count),
            "total_tokens": float(story.total_tokens or 0),
        }
        for story_id, story in stories.items()
    }

    eval_stmt = (
        select(
            StoryEvaluation.story_id,
            func.avg(StoryEvaluation.overall_score).label("avg_overall_score"),
            func.avg(StoryEvaluation.coherence_score).label("avg_coherence_score"),
            func.avg(StoryEvaluation.novelty_score).label("avg_novelty_score"),
            func.avg(StoryEvaluation.engagement_score).label("avg_engagement_score"),
            func.avg(StoryEvaluation.pacing_score).label("avg_pacing_score"),
        )
        .group_by(StoryEvaluation.story_id)
    )

    eval_rows = await session.execute(eval_stmt)
    for row in eval_rows:
        data = aggregates.setdefault(row.story_id, {})
        if row.avg_overall_score is not None:
            data["avg_overall_score"] = float(row.avg_overall_score)
        if row.avg_coherence_score is not None:
            data["avg_coherence_score"] = float(row.avg_coherence_score)
        if row.avg_novelty_score is not None:
            data["avg_novelty_score"] = float(row.avg_novelty_score)
        if row.avg_engagement_score is not None:
            data["avg_engagement_score"] = float(row.avg_engagement_score)
        if row.avg_pacing_score is not None:
            data["avg_pacing_score"] = float(row.avg_pacing_score)

    chaos_stmt = (
        select(
            Chapter.story_id,
            func.avg(Chapter.absurdity).label("avg_absurdity"),
            func.avg(Chapter.surrealism).label("avg_surrealism"),
            func.avg(Chapter.ridiculousness).label("avg_ridiculousness"),
            func.avg(Chapter.insanity).label("avg_insanity"),
        )
        .group_by(Chapter.story_id)
    )

    chaos_rows = await session.execute(chaos_stmt)
    for row in chaos_rows:
        data = aggregates.setdefault(row.story_id, {})
        if row.avg_absurdity is not None:
            data["avg_absurdity"] = float(row.avg_absurdity)
        if row.avg_surrealism is not None:
            data["avg_surrealism"] = float(row.avg_surrealism)
        if row.avg_ridiculousness is not None:
            data["avg_ridiculousness"] = float(row.avg_ridiculousness)
        if row.avg_insanity is not None:
            data["avg_insanity"] = float(row.avg_insanity)

    metric_definitions = [
        {
            "key": "avg_overall_score",
            "label": "Average Evaluation Score",
            "description": "Mean overall evaluation across all chapters.",
            "group": "Evaluation Scores",
            "order": 1,
            "decimals": 2,
            "higher_is_better": True,
        },
        {
            "key": "avg_coherence_score",
            "label": "Average Coherence",
            "description": "How consistently the narrative holds together chapter to chapter.",
            "group": "Evaluation Scores",
            "order": 2,
            "decimals": 2,
            "higher_is_better": True,
        },
        {
            "key": "avg_novelty_score",
            "label": "Average Novelty",
            "description": "Inventiveness and originality rated by the evaluator.",
            "group": "Evaluation Scores",
            "order": 3,
            "decimals": 2,
            "higher_is_better": True,
        },
        {
            "key": "avg_engagement_score",
            "label": "Average Engagement",
            "description": "Reader engagement rating averaged across evaluations.",
            "group": "Evaluation Scores",
            "order": 4,
            "decimals": 2,
            "higher_is_better": True,
        },
        {
            "key": "avg_pacing_score",
            "label": "Average Pacing",
            "description": "Smoothness of pacing across the story arc.",
            "group": "Evaluation Scores",
            "order": 5,
            "decimals": 2,
            "higher_is_better": True,
        },
        {
            "key": "avg_absurdity",
            "label": "Absurdity",
            "description": "Average absurdity rating for generated chapters.",
            "group": "Chaos Parameters",
            "order": 6,
            "decimals": 3,
            "higher_is_better": True,
        },
        {
            "key": "avg_surrealism",
            "label": "Surrealism",
            "description": "Average surrealism level across chapters.",
            "group": "Chaos Parameters",
            "order": 7,
            "decimals": 3,
            "higher_is_better": True,
        },
        {
            "key": "avg_ridiculousness",
            "label": "Ridiculousness",
            "description": "Average ridiculousness injection per chapter.",
            "group": "Chaos Parameters",
            "order": 8,
            "decimals": 3,
            "higher_is_better": True,
        },
        {
            "key": "avg_insanity",
            "label": "Insanity",
            "description": "Average insanity score keeping the chaos dial pegged.",
            "group": "Chaos Parameters",
            "order": 9,
            "decimals": 3,
            "higher_is_better": True,
        },
        {
            "key": "chapter_count",
            "label": "Chapters Published",
            "description": "Total number of chapters released for the story.",
            "group": "Story Progress",
            "order": 10,
            "decimals": 0,
            "higher_is_better": True,
        },
        {
            "key": "total_tokens",
            "label": "Tokens Consumed",
            "description": "Cumulative token usage across the full narrative run.",
            "group": "Story Progress",
            "order": 11,
            "decimals": 0,
            "higher_is_better": True,
        },
    ]

    metric_results: list[MetricExtremes] = []

    for definition in metric_definitions:
        key = definition["key"]
        values: list[tuple[uuid.UUID, float]] = []
        for story_id, metrics in aggregates.items():
            value = metrics.get(key)
            if value is None:
                continue
            values.append((story_id, float(value)))

        if not values:
            continue

        best_story_id, best_value = max(values, key=lambda item: item[1])
        worst_story_id, worst_value = min(values, key=lambda item: item[1])

        def build_entry(story_id: uuid.UUID, value: float) -> MetricStoryResult:
            story = stories[story_id]
            return MetricStoryResult(
                story_id=story.id,
                title=story.title,
                status=story.status,
                cover_image_url=story.cover_image_url,
                chapter_count=story.chapter_count,
                completed_at=story.completed_at,
                value=value,
            )

        metric_results.append(
            MetricExtremes(
                key=key,
                label=definition["label"],
                description=definition.get("description"),
                group=definition["group"],
                order=definition["order"],
                unit=definition.get("unit"),
                decimals=definition.get("decimals", 2),
                higher_is_better=definition.get("higher_is_better", True),
                best=build_entry(best_story_id, best_value),
                worst=build_entry(worst_story_id, worst_value),
            )
        )

    metric_results.sort(key=lambda item: item.order)
    return {"metrics": [metric.model_dump() for metric in metric_results]}


@app.websocket("/ws/stories")
async def stories_ws(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:  # noqa: BLE001
        await ws_manager.disconnect(websocket)
        logger.exception("WebSocket error")


@app.post("/api/admin/spawn", status_code=201)
async def admin_spawn_story(
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    """Spawn a new story. If at max active stories, terminate the oldest active story first."""
    runtime_config = await get_runtime_config(session)
    
    # Check if we're at max active stories
    count_stmt = select(func.count()).select_from(Story).where(Story.status == "active")
    active_count = (await session.execute(count_stmt)).scalar_one()
    
    if active_count >= runtime_config.max_active_stories:
        # Find and terminate the oldest active story
        oldest_stmt = (
            select(Story)
            .where(Story.status == "active")
            .order_by(Story.created_at.asc())
            .limit(1)
        )
        oldest_story = (await session.execute(oldest_stmt)).scalar_one_or_none()
        if oldest_story:
            oldest_story.status = "completed"
            oldest_story.completed_at = datetime.utcnow()
            oldest_story.completion_reason = "Replaced by new story"
            # Generate cover image for the terminated story
            if not oldest_story.cover_image_url:
                try:
                    cover_url = await generate_cover_image(oldest_story.title, oldest_story.premise)
                    if cover_url:
                        oldest_story.cover_image_url = cover_url
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Failed to generate cover image for replaced story %s", oldest_story.title)
            await session.flush()
            logger.info("Terminated oldest story '%s' to make room for new story", oldest_story.title)
    
    # Spawn the new story
    payload = await spawn_new_story(runtime_config)
    story = Story(
        title=payload["title"],
        premise=payload["premise"],
        status="active",
        theme_json=payload.get("theme_json"),
        absurdity_initial=payload.get("absurdity_initial", 0.1),
        surrealism_initial=payload.get("surrealism_initial", 0.1),
        ridiculousness_initial=payload.get("ridiculousness_initial", 0.1),
        insanity_initial=payload.get("insanity_initial", 0.1),
        absurdity_increment=payload.get("absurdity_increment", 0.05),
        surrealism_increment=payload.get("surrealism_increment", 0.05),
        ridiculousness_increment=payload.get("ridiculousness_increment", 0.05),
        insanity_increment=payload.get("insanity_increment", 0.05),
        style_authors=payload.get("style_authors"),
        narrative_perspective=payload.get("narrative_perspective"),
        tone=payload.get("tone"),
        genre_tags=payload.get("genre_tags"),
    )
    session.add(story)
    await session.flush()
    stmt = (
        select(Story)
        .where(Story.id == story.id)
        .options(selectinload(Story.chapters), selectinload(Story.evaluations))
    )
    story_obj = (await session.execute(stmt)).scalars().first()
    if not story_obj:
        raise HTTPException(status_code=500, detail="Failed to spawn story")
    
    await session.commit()
    
    if settings.enable_websocket:
        await ws_manager.broadcast({
            "type": "new_story",
            "story_id": str(story_obj.id),
        })

    universe_context = await _get_story_universe_context(session, story_obj.id)
    overrides = await _get_story_entity_overrides(session, story_obj.id)
    return StoryDetail.from_model(
        story_obj, universe=universe_context, overrides=overrides
    ).model_dump()


@app.delete("/api/stories/{story_id}")
async def delete_story(story_id: uuid.UUID, session: SessionDep) -> dict[str, Any]:
    """Permanently delete a story and all its chapters/evaluations."""
    stmt = select(Story).where(Story.id == story_id)
    story = (await session.execute(stmt)).scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    title = story.title
    session.delete(story)
    await session.commit()
    
    logger.info("Deleted story: %s", title)
    
    return {"message": f"Story '{title}' deleted successfully", "deleted": True}


@app.post("/api/admin/backfill-cover-images")
async def admin_backfill_cover_images(
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    """Generate cover images for all completed stories without one."""
    stmt = select(Story).where(
        Story.status == "completed",
        Story.cover_image_url.is_(None)
    )
    
    stories = (await session.execute(stmt)).scalars().all()
    
    if not stories:
        return {
            "message": "No stories need cover images",
            "processed": 0,
            "success": 0,
            "failed": 0
        }
    
    logger.info("Found %d completed stories without cover images", len(stories))
    
    success_count = 0
    failed_count = 0
    
    for story in stories:
        logger.info("Generating cover image for story: %s", story.title)
        try:
            cover_url = await generate_cover_image(story.title, story.premise)
            if cover_url:
                story.cover_image_url = cover_url
                await session.flush()
                success_count += 1
                logger.info("✓ Cover image generated for: %s", story.title)
            else:
                failed_count += 1
                logger.warning("✗ No URL returned for: %s", story.title)
        except Exception as exc:
            failed_count += 1
            logger.exception("Failed to generate cover for %s: %s", story.title, exc)
    
    await session.commit()
    
    return {
        "message": "Backfill complete",
        "processed": len(stories),
        "success": success_count,
        "failed": failed_count
    }


@app.post("/api/admin/reset", status_code=202)
async def admin_reset_system(
    session: SessionDep,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    """Clear all stories and reset runtime configuration to defaults."""
    story_count = (
        await session.execute(select(func.count()).select_from(Story))
    ).scalar_one()

    # Delete stories (cascades to chapters/evaluations)
    await session.execute(delete(Story))
    # Reset runtime config to .env defaults
    await session.execute(delete(SystemConfig))
    await session.commit()

    if settings.enable_websocket:
        await ws_manager.broadcast(
            {
                "type": "system_reset",
                "deleted_stories": story_count,
            }
        )

    logger.info("System reset performed: %s stories removed", story_count)
    return {
        "message": "System reset to configuration defaults",
        "deleted_stories": story_count,
    }


@app.exception_handler(NoResultFound)
async def handle_not_found(_: Request, exc: NoResultFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


from debug_routes import router as debug_router

app.include_router(debug_router)

__all__ = ["app"]
