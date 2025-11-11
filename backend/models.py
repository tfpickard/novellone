import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500))
    premise: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    chapter_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    theme_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_chapter_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Style and metadata
    style_authors: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)  # List of 1-3 author names
    narrative_perspective: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "first-person", "third-person-omniscient"
    tone: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "dark", "humorous", "philosophical"
    genre_tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)  # Additional genre/style tags
    estimated_reading_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Total estimated reading time

    # Chaos parameters - initial values set at story creation
    absurdity_initial: Mapped[float] = mapped_column(Float, default=0.1)
    surrealism_initial: Mapped[float] = mapped_column(Float, default=0.1)
    ridiculousness_initial: Mapped[float] = mapped_column(Float, default=0.1)
    insanity_initial: Mapped[float] = mapped_column(Float, default=0.1)
    
    # Increments per chapter
    absurdity_increment: Mapped[float] = mapped_column(Float, default=0.05)
    surrealism_increment: Mapped[float] = mapped_column(Float, default=0.05)
    ridiculousness_increment: Mapped[float] = mapped_column(Float, default=0.05)
    insanity_increment: Mapped[float] = mapped_column(Float, default=0.05)

    # Content axes configuration stored per story
    content_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", order_by="Chapter.chapter_number"
    )
    evaluations: Mapped[list["StoryEvaluation"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", order_by="StoryEvaluation.chapter_number"
    )


class StoryCorpus(Base):
    __tablename__ = "story_corpora"

    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_chapter_number: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)

    story: Mapped[Story] = relationship(backref="corpus", uselist=False)


class StoryEntity(Base):
    __tablename__ = "story_entities"
    __table_args__ = (UniqueConstraint("story_id", "name", name="uq_story_entity"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(64), default="unknown")
    aliases: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    first_seen_chapter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_chapter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    story: Mapped[Story] = relationship(backref="entities")


class StoryTheme(Base):
    __tablename__ = "story_themes"
    __table_args__ = (UniqueConstraint("story_id", "name", name="uq_story_theme"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    story: Mapped[Story] = relationship(backref="derived_themes")


class StoryEntityOverride(Base):
    __tablename__ = "story_entity_overrides"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(32))
    target_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    story: Mapped[Story | None] = relationship(backref="entity_overrides")


class StoryUniverseLink(Base):
    __tablename__ = "story_universe_links"
    __table_args__ = (UniqueConstraint("source_story_id", "target_story_id", name="uq_story_link"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"))
    target_story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"))
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    shared_entities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    shared_themes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UniverseCluster(Base):
    __tablename__ = "universe_clusters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0)
    cohesion: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UniverseClusterMembership(Base):
    __tablename__ = "universe_cluster_memberships"

    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universe_clusters.id", ondelete="CASCADE"))
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cluster: Mapped[UniverseCluster] = relationship(backref="members")
    story: Mapped[Story] = relationship(backref="universe_membership")


class MetaAnalysisRun(Base):
    __tablename__ = "meta_analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="success")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    processed_items: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("story_id", "chapter_number", name="uq_story_chapter"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"))
    chapter_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Chaos parameters - actual values for this chapter as returned by OpenAI
    absurdity: Mapped[float | None] = mapped_column(Float, nullable=True)
    surrealism: Mapped[float | None] = mapped_column(Float, nullable=True)
    ridiculousness: Mapped[float | None] = mapped_column(Float, nullable=True)
    insanity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Chapter-level content intensity readings per axis
    content_levels: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    story: Mapped[Story] = relationship(back_populates="chapters")


class StoryEvaluation(Base):
    __tablename__ = "story_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"))
    chapter_number: Mapped[int] = mapped_column(Integer)
    overall_score: Mapped[float] = mapped_column(Float)
    coherence_score: Mapped[float] = mapped_column(Float)
    novelty_score: Mapped[float] = mapped_column(Float)
    engagement_score: Mapped[float] = mapped_column(Float)
    pacing_score: Mapped[float] = mapped_column(Float)
    should_continue: Mapped[bool] = mapped_column(Boolean, default=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    story: Mapped[Story] = relationship(back_populates="evaluations")


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = [
    "Base",
    "Story",
    "Chapter",
    "StoryEvaluation",
    "SystemConfig",
    "StoryCorpus",
    "StoryEntity",
    "StoryTheme",
    "StoryUniverseLink",
    "UniverseCluster",
    "UniverseClusterMembership",
]
