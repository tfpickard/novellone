import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from config import get_settings
from config_store import RuntimeConfig, get_runtime_config
from database import get_session
from models import Chapter, Story, StoryEvaluation
from meta import CorpusExtractionService, EntityExtractionService, UniverseGraphService
from story_evaluator import evaluate_story
from story_generator import generate_chapter, generate_cover_image, spawn_new_story
from websocket_manager import ws_manager

logger = logging.getLogger(__name__)

settings = get_settings()


class BackgroundWorker:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self._lock = asyncio.Lock()
        self._corpus_service = CorpusExtractionService()
        self._entity_service = EntityExtractionService()
        self._universe_service = UniverseGraphService()
        self._stories_to_refresh: set[uuid.UUID] = set()
        self._last_universe_refresh: datetime | None = None

    async def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.add_job(self._tick, "interval", seconds=settings.worker_tick_interval)
            self.scheduler.start()
            logger.info("Background worker started")

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Background worker stopped")

    async def _tick(self) -> None:
        if self._lock.locked():
            logger.debug("Background tick skipped: previous run still in progress")
            return

        async with self._lock:
            tick_start = time.perf_counter()
            logger.debug("Background tick started")
            try:
                await self._run_cycle()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Background cycle failed: %s", exc)
            finally:
                duration_ms = (time.perf_counter() - tick_start) * 1000
                logger.debug("Background tick finished in %.2f ms", duration_ms)

    async def _run_cycle(self) -> None:
        async with get_session() as session:
            cycle_start = time.perf_counter()
            logger.debug("Fetching runtime configuration")
            runtime_config = await get_runtime_config(session)
            active_stmt = (
                select(Story)
                .where(Story.status == "active")
                .options(selectinload(Story.chapters), selectinload(Story.evaluations))
                .order_by(Story.created_at)
            )
            active_stories = list((await session.execute(active_stmt)).scalars())
            logger.debug("Active stories loaded: %d", len(active_stories))

            now = datetime.utcnow()
            for story in active_stories:
                await session.refresh(
                    story,
                    attribute_names=["chapter_count", "last_chapter_at", "status"],
                )
                await self._process_story(session, story, now, runtime_config)

            await session.commit()

            await self._maintain_story_count(session, runtime_config)
            await session.commit()

            await self._run_meta_analysis(session, active_stories)
            await session.commit()

            cycle_duration_ms = (time.perf_counter() - cycle_start) * 1000
            logger.debug("Background cycle completed in %.2f ms", cycle_duration_ms)

    async def _process_story(
        self,
        session,
        story: Story,
        now: datetime,
        config: RuntimeConfig,
    ) -> None:
        logger.debug(
            "Processing story %s (status=%s chapters=%d last_chapter_at=%s)",
            story.id,
            story.status,
            story.chapter_count,
            story.last_chapter_at,
        )
        if story.status != "active":
            logger.debug("Story %s is not active; skipping", story.id)
            return

        if story.chapter_count >= config.max_chapters_per_story:
            await self._complete_story(session, story, "Reached max chapters")
            return

        last_chapter = story.last_chapter_at or story.created_at
        elapsed = (now - last_chapter).total_seconds()
        if elapsed >= config.chapter_interval_seconds:
            await self._create_chapter(session, story, config)
        else:
            logger.debug(
                "Skipping chapter for story %s; %.1fs elapsed (needs %.1fs)",
                story.id,
                elapsed,
                config.chapter_interval_seconds,
            )

        if (
            story.chapter_count >= settings.min_chapters_before_eval
            and story.chapter_count % config.evaluation_interval_chapters == 0
        ):
            logger.debug(
                "Triggering evaluation for story %s at chapter %d",
                story.id,
                story.chapter_count,
            )
            await self._evaluate_story(session, story, config)
        else:
            logger.debug(
                "No evaluation for story %s this cycle (chapter_count=%d, interval=%d)",
                story.id,
                story.chapter_count,
                config.evaluation_interval_chapters,
            )

    async def _create_chapter(
        self, session, story: Story, config: RuntimeConfig
    ) -> Chapter:
        chapters_stmt = (
            select(Chapter)
            .where(Chapter.story_id == story.id)
            .order_by(Chapter.chapter_number.desc())
            .limit(config.context_window_chapters)
        )
        recent = list((await session.execute(chapters_stmt)).scalars())
        recent.reverse()
        chapter_data = await generate_chapter(story, recent, chapter_number=story.chapter_count + 1)
        chapter = Chapter(story_id=story.id, **chapter_data)
        session.add(chapter)
        story.chapter_count += 1
        story.last_chapter_at = datetime.utcnow()
        tokens = chapter_data.get("tokens_used") or 0
        story.total_tokens = (story.total_tokens or 0) + tokens
        self._stories_to_refresh.add(story.id)
        await session.flush()
        await session.refresh(chapter)
        if settings.enable_websocket:
            await ws_manager.broadcast({
                "type": "new_chapter",
                "story_id": str(story.id),
                "chapter": {
                    "id": str(chapter.id),
                    "chapter_number": chapter.chapter_number,
                    "content": chapter.content,
                    "created_at": chapter.created_at.isoformat(),
                    "tokens_used": chapter.tokens_used,
                    "generation_time_ms": chapter.generation_time_ms,
                    "model_used": chapter.model_used,
                    "absurdity": chapter.absurdity,
                    "surrealism": chapter.surrealism,
                    "ridiculousness": chapter.ridiculousness,
                    "insanity": chapter.insanity,
                },
            })
        logger.info(
            "Generated chapter %s for story %s (%s tokens, %s ms)",
            chapter.chapter_number,
            story.title,
            tokens,
            chapter.generation_time_ms,
        )
        return chapter

    async def _evaluate_story(
        self, session, story: Story, config: RuntimeConfig
    ) -> None:
        chapters_stmt = select(Chapter).where(Chapter.story_id == story.id).order_by(Chapter.chapter_number)
        chapters = list((await session.execute(chapters_stmt)).scalars())
        logger.debug(
            "Evaluating story %s with %d chapters (quality threshold: %.2f)",
            story.id, len(chapters), config.quality_score_min
        )
        result = await evaluate_story(story, chapters, quality_threshold=config.quality_score_min)
        evaluation = StoryEvaluation(
            story_id=story.id,
            chapter_number=story.chapter_count,
            overall_score=result.get("overall_score", 0.0),
            coherence_score=result.get("coherence_score", 0.0),
            novelty_score=result.get("novelty_score", 0.0),
            engagement_score=result.get("engagement_score", 0.0),
            pacing_score=result.get("pacing_score", 0.0),
            should_continue=bool(result.get("should_continue", True)),
            reasoning=result.get("reasoning"),
            issues=result.get("issues", []),
        )
        session.add(evaluation)
        await session.flush()
        if (
            not evaluation.should_continue
            or evaluation.overall_score < config.quality_score_min
        ):
            reason = evaluation.reasoning or "Quality threshold not met"
            await self._complete_story(session, story, reason)
        logger.info(
            "Evaluated story %s: overall=%.2f should_continue=%s",
            story.title,
            evaluation.overall_score,
            evaluation.should_continue,
        )

    async def generate_chapter_manual(
        self, session, story: Story, config: RuntimeConfig
    ) -> Chapter:
        async with self._lock:
            chapter = await self._create_chapter(session, story, config)

            if (
                story.chapter_count >= settings.min_chapters_before_eval
                and story.chapter_count % config.evaluation_interval_chapters == 0
            ):
                await self._evaluate_story(session, story, config)

        return chapter

    async def _complete_story(self, session, story: Story, reason: str) -> None:
        if story.status != "completed":
            story.status = "completed"
            story.completed_at = datetime.utcnow()
            story.completion_reason = reason
            await session.flush()
            self._stories_to_refresh.add(story.id)
            
            # Generate cover image for the completed story (only if we don't have one)
            if not story.cover_image_url:
                logger.info("Generating cover image for completed story: %s", story.title)
                try:
                    cover_url = await generate_cover_image(story.title, story.premise)
                    if cover_url:
                        story.cover_image_url = cover_url
                        await session.flush()
                        logger.info("✓ Cover image saved for story %s", story.title)
                    else:
                        logger.warning("✗ No cover image URL returned for story %s", story.title)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Failed to generate cover image for story %s: %s", story.title, exc)
            else:
                logger.debug("Story %s already has cover image, skipping generation", story.title)
            
            if settings.enable_websocket:
                await ws_manager.broadcast(
                    {
                        "type": "story_completed",
                        "story_id": str(story.id),
                        "reason": reason,
                        "cover_image_url": story.cover_image_url,
                    }
                )
            logger.info("Story %s completed: %s", story.title, reason)

    async def _maintain_story_count(self, session, config: RuntimeConfig) -> None:
        count_stmt = select(func.count()).select_from(Story).where(Story.status == "active")
        active_count = (await session.execute(count_stmt)).scalar_one()
        logger.debug(
            "Maintaining story count: active=%d min=%d max=%d",
            active_count,
            config.min_active_stories,
            config.max_active_stories,
        )

        if active_count < config.min_active_stories:
            needed = config.min_active_stories - active_count
            logger.debug("Spawning %d stories to reach minimum active target", needed)
            for _ in range(needed):
                await self._spawn_story(session)
        elif active_count > config.max_active_stories:
            excess = active_count - config.max_active_stories
            logger.debug("Completing %d stories to enforce maximum active limit", excess)
            victims_stmt = (
                select(Story)
                .where(Story.status == "active")
                .order_by(Story.created_at.desc())
                .limit(excess)
            )
            victims = list((await session.execute(victims_stmt)).scalars())
            for story in victims:
                await self._complete_story(session, story, "Reduced to maintain limit")

    async def _spawn_story(self, session) -> None:
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
        self._stories_to_refresh.add(story.id)
        logger.info("Spawned new story: %s", story.title)

    async def _run_meta_analysis(self, session, loaded_stories: list[Story]) -> None:
        candidates = set(self._stories_to_refresh)
        needs_universe = self._needs_universe_refresh()
        if not candidates and not needs_universe:
            return

        stories_by_id = {story.id: story for story in loaded_stories}
        missing_ids = [story_id for story_id in candidates if story_id not in stories_by_id]
        if missing_ids:
            stmt = (
                select(Story)
                .where(Story.id.in_(missing_ids))
                .options(selectinload(Story.chapters))
            )
            fetched = list((await session.execute(stmt)).scalars())
            stories_by_id.update({story.id: story for story in fetched})

        target_stories = [stories_by_id[story_id] for story_id in candidates if story_id in stories_by_id]

        if target_stories:
            corpora = await self._corpus_service.refresh_story_corpora(session, target_stories)
            await self._entity_service.refresh_entities(session, target_stories, corpora)
            self._stories_to_refresh.difference_update({story.id for story in target_stories})

        if needs_universe:
            await self._universe_service.refresh_universe(session)
            self._last_universe_refresh = datetime.utcnow()

    def _needs_universe_refresh(self) -> bool:
        if self._last_universe_refresh is None:
            return True
        return (datetime.utcnow() - self._last_universe_refresh) >= timedelta(hours=6)


def create_worker() -> BackgroundWorker:
    return BackgroundWorker()


worker = create_worker()

__all__ = ["BackgroundWorker", "create_worker", "worker"]
