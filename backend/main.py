from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any

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
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import selectinload

from background_worker import worker
from config import get_settings
from config_store import apply_config_updates, get_runtime_config
from logging_config import configure_logging
from database import get_session
from models import Chapter, Story, StoryEvaluation, SystemConfig
from story_generator import generate_cover_image, spawn_new_story
from websocket_manager import ws_manager

settings = get_settings()
configure_logging(settings)

logger = logging.getLogger(__name__)

app = FastAPI(title="Eternal Stories", version="1.0.0")

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


SessionDep = Annotated[Any, Depends(get_db_session)]
class ChapterRead(BaseModel):
    id: uuid.UUID
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

    @classmethod
    def from_model(cls, chapter: Chapter) -> "ChapterRead":
        return cls(
            id=chapter.id,
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
    absurdity_initial: float = 0.1
    surrealism_initial: float = 0.1
    ridiculousness_initial: float = 0.1
    insanity_initial: float = 0.1
    absurdity_increment: float = 0.05
    surrealism_increment: float = 0.05
    ridiculousness_increment: float = 0.05
    insanity_increment: float = 0.05

    @classmethod
    def from_model(cls, story: Story) -> "StorySummary":
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
            absurdity_initial=story.absurdity_initial,
            surrealism_initial=story.surrealism_initial,
            ridiculousness_initial=story.ridiculousness_initial,
            insanity_initial=story.insanity_initial,
            absurdity_increment=story.absurdity_increment,
            surrealism_increment=story.surrealism_increment,
            ridiculousness_increment=story.ridiculousness_increment,
            insanity_increment=story.insanity_increment,
        )


class StoryDetail(StorySummary):
    completion_reason: str | None
    evaluations: list[StoryEvaluationRead]
    chapters: list[ChapterRead]

    @classmethod
    def from_model(cls, story: Story) -> "StoryDetail":
        return cls(
            **StorySummary.from_model(story).model_dump(),
            completion_reason=story.completion_reason,
            evaluations=[StoryEvaluationRead.from_model(e) for e in story.evaluations],
            chapters=[ChapterRead.from_model(c) for c in story.chapters],
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


@app.get("/api/config")
async def get_public_config(session: SessionDep) -> dict[str, Any]:
    runtime = await get_runtime_config(session)
    return runtime.as_dict()


@app.patch("/api/config")
async def update_public_config(payload: ConfigUpdate, session: SessionDep) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    try:
        runtime = await apply_config_updates(session, data)
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await session.commit()
    return runtime.as_dict()


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
    return StoryDetail.from_model(story).model_dump()


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
    return StoryDetail.from_model(story_obj).model_dump()


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
        "recent_activity": [
            ChapterRead.from_model(c).model_dump() for c in recent_activity
        ],
    }


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
async def admin_spawn_story(session: SessionDep) -> dict[str, Any]:
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
    payload = await spawn_new_story()
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
    
    return StoryDetail.from_model(story_obj).model_dump()


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
async def admin_backfill_cover_images(session: SessionDep) -> dict[str, Any]:
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
async def admin_reset_system(session: SessionDep) -> dict[str, Any]:
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
