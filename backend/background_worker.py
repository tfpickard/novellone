import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from config import get_settings
from config_store import RuntimeConfig, get_runtime_config
from database import get_session
from models import Chapter, Story, StoryEvaluation
from story_evaluator import evaluate_story
from story_generator import generate_chapter, spawn_new_story
from websocket_manager import ws_manager

logger = logging.getLogger(__name__)

settings = get_settings()


class BackgroundWorker:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self._lock = asyncio.Lock()

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
        if not self._lock.locked():
            async with self._lock:
                try:
                    await self._run_cycle()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Background cycle failed: %s", exc)

    async def _run_cycle(self) -> None:
        async with get_session() as session:
            runtime_config = await get_runtime_config(session)
            active_stmt = (
                select(Story)
                .where(Story.status == "active")
                .options(selectinload(Story.chapters), selectinload(Story.evaluations))
                .order_by(Story.created_at)
            )
            active_stories = list((await session.execute(active_stmt)).scalars())

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

    async def _process_story(
        self,
        session,
        story: Story,
        now: datetime,
        config: RuntimeConfig,
    ) -> None:
        if story.status != "active":
            return

        if story.chapter_count >= config.max_chapters_per_story:
            await self._complete_story(session, story, "Reached max chapters")
            return

        last_chapter = story.last_chapter_at or story.created_at
        if (now - last_chapter) >= timedelta(seconds=config.chapter_interval_seconds):
            await self._create_chapter(session, story, config)

        if (
            story.chapter_count >= settings.min_chapters_before_eval
            and story.chapter_count % config.evaluation_interval_chapters == 0
        ):
            await self._evaluate_story(session, story, config)

    async def _create_chapter(
        self, session, story: Story, config: RuntimeConfig
    ) -> None:
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
                },
            })
        logger.info(
            "Generated chapter %s for story %s (%s tokens, %s ms)",
            chapter.chapter_number,
            story.title,
            tokens,
            chapter.generation_time_ms,
        )

    async def _evaluate_story(
        self, session, story: Story, config: RuntimeConfig
    ) -> None:
        chapters_stmt = select(Chapter).where(Chapter.story_id == story.id).order_by(Chapter.chapter_number)
        chapters = list((await session.execute(chapters_stmt)).scalars())
        result = await evaluate_story(story, chapters)
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

    async def _complete_story(self, session, story: Story, reason: str) -> None:
        if story.status != "completed":
            story.status = "completed"
            story.completed_at = datetime.utcnow()
            story.completion_reason = reason
            await session.flush()
            if settings.enable_websocket:
                await ws_manager.broadcast(
                    {
                        "type": "story_completed",
                        "story_id": str(story.id),
                        "reason": reason,
                    }
                )
            logger.info("Story %s completed: %s", story.title, reason)

    async def _maintain_story_count(self, session, config: RuntimeConfig) -> None:
        count_stmt = select(func.count()).select_from(Story).where(Story.status == "active")
        active_count = (await session.execute(count_stmt)).scalar_one()

        if active_count < config.min_active_stories:
            needed = config.min_active_stories - active_count
            for _ in range(needed):
                await self._spawn_story(session)
        elif active_count > config.max_active_stories:
            excess = active_count - config.max_active_stories
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
        )
        session.add(story)
        await session.flush()
        logger.info("Spawned new story: %s", story.title)


def create_worker() -> BackgroundWorker:
    return BackgroundWorker()


worker = create_worker()

__all__ = ["BackgroundWorker", "create_worker", "worker"]
