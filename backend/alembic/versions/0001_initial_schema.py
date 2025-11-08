"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stories",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("premise", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("completion_reason", sa.Text(), nullable=True),
        sa.Column("chapter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("theme_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("last_chapter_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_stories_status", "stories", ["status"])
    op.create_index("ix_stories_created_at", "stories", ["created_at"])

    op.create_table(
        "chapters",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("story_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("generation_time_ms", sa.Integer(), nullable=True),
        sa.Column("model_used", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("story_id", "chapter_number", name="uq_story_chapter"),
    )
    op.create_index("ix_chapters_created_at", "chapters", ["created_at"])

    op.create_table(
        "story_evaluations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("story_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("coherence_score", sa.Float(), nullable=False),
        sa.Column("novelty_score", sa.Float(), nullable=False),
        sa.Column("engagement_score", sa.Float(), nullable=False),
        sa.Column("pacing_score", sa.Float(), nullable=False),
        sa.Column("should_continue", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("issues", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("story_evaluations")
    op.drop_index("ix_chapters_created_at", table_name="chapters")
    op.drop_table("chapters")
    op.drop_index("ix_stories_created_at", table_name="stories")
    op.drop_index("ix_stories_status", table_name="stories")
    op.drop_table("stories")
