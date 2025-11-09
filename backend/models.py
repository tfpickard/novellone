import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
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

    # Optional link to a universe prompt
    universe_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("universe_prompts.id", ondelete="SET NULL"), nullable=True
    )

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", order_by="Chapter.chapter_number"
    )
    evaluations: Mapped[list["StoryEvaluation"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", order_by="StoryEvaluation.chapter_number"
    )
    universe_elements: Mapped[list["UniverseElement"]] = relationship(
        back_populates="source_story", cascade="all, delete-orphan"
    )
    cohesion_metrics: Mapped[list["CohesionMetric"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )
    universe_prompt: Mapped["UniversePrompt | None"] = relationship()


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


class UniversePrompt(Base):
    __tablename__ = "universe_prompts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Structured universe content
    characters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {name: {traits, background, relationships}}
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)    # {name: {description, rules, history}}
    themes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)      # {theme: {description, examples}}
    lore: Mapped[dict | None] = mapped_column(JSONB, nullable=True)        # {topic: {facts, constraints}}
    narrative_constraints: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)  # Rules for stories

    # Generation weights (0.0-1.0)
    character_weight: Mapped[float] = mapped_column(Float, default=0.5)
    setting_weight: Mapped[float] = mapped_column(Float, default=0.5)
    theme_weight: Mapped[float] = mapped_column(Float, default=0.5)
    lore_weight: Mapped[float] = mapped_column(Float, default=0.5)

    # Relationships
    elements: Mapped[list["UniverseElement"]] = relationship(
        back_populates="universe_prompt", cascade="all, delete-orphan"
    )
    cohesion_metrics: Mapped[list["CohesionMetric"]] = relationship(
        back_populates="universe_prompt", cascade="all, delete-orphan"
    )
    stories: Mapped[list["Story"]] = relationship()


class UniverseElement(Base):
    __tablename__ = "universe_elements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    universe_prompt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("universe_prompts.id", ondelete="CASCADE")
    )
    source_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE")
    )

    element_type: Mapped[str] = mapped_column(String(50), index=True)  # character, setting, theme, lore
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Type-specific data

    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    universe_prompt: Mapped[UniversePrompt] = relationship(back_populates="elements")
    source_story: Mapped[Story] = relationship(back_populates="universe_elements")


class CohesionMetric(Base):
    __tablename__ = "cohesion_metrics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"))
    universe_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("universe_prompts.id", ondelete="CASCADE"), nullable=True
    )

    # Cohesion scores (0.0-1.0)
    character_recurrence_score: Mapped[float] = mapped_column(Float, default=0.0)
    thematic_overlap_score: Mapped[float] = mapped_column(Float, default=0.0)
    timeline_continuity_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_cohesion_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Details about linkages found
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Specific connections

    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    story: Mapped[Story] = relationship(back_populates="cohesion_metrics")
    universe_prompt: Mapped[UniversePrompt | None] = relationship(back_populates="cohesion_metrics")


__all__ = ["Base", "Story", "Chapter", "StoryEvaluation", "SystemConfig",
           "UniversePrompt", "UniverseElement", "CohesionMetric"]
