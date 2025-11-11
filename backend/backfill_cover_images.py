"""Script to generate cover images for all completed stories that don't have one."""
import asyncio
import logging

from sqlalchemy import select

from database import get_session
from models import Story
from story_generator import generate_cover_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_cover_images():
    """Generate cover images for all completed stories without one."""
    async with get_session() as session:
        # Find all completed stories without a cover image
        stmt = select(Story).where(
            Story.status == "completed",
            Story.cover_image_url.is_(None)
        )
        
        stories = (await session.execute(stmt)).scalars().all()
        
        if not stories:
            logger.info("No stories need cover images")
            return
        
        logger.info("Found %d completed stories without cover images", len(stories))
        
        for story in stories:
            logger.info("Generating cover image for story: %s", story.title)
            try:
                cover_url = await generate_cover_image(
                    story.title,
                    story.premise,
                    story.content_settings,
                )
                if cover_url:
                    story.cover_image_url = cover_url
                    await session.flush()
                    logger.info("✓ Cover image generated for: %s", story.title)
                else:
                    logger.warning("✗ No URL returned for: %s", story.title)
            except Exception as exc:
                logger.exception("Failed to generate cover for %s: %s", story.title, exc)
        
        await session.commit()
        logger.info("Backfill complete!")


if __name__ == "__main__":
    asyncio.run(backfill_cover_images())

