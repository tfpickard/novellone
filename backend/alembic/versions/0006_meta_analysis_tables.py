"""meta analysis tables

Revision ID: 0006_meta_analysis_tables
Revises: 0005
Create Date: 2024-05-15 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0006_meta_analysis_tables"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "story_corpora",
        sa.Column("story_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_chapter_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("story_id"),
    )

    op.create_table(
        "story_entities",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("aliases", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("first_seen_chapter", sa.Integer(), nullable=True),
        sa.Column("last_seen_chapter", sa.Integer(), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id", "name", name="uq_story_entity"),
    )

    op.create_table(
        "story_themes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id", "name", name="uq_story_theme"),
    )

    op.create_table(
        "universe_clusters",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cohesion", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "universe_cluster_memberships",
        sa.Column("story_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cluster_id"], ["universe_clusters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("story_id"),
    )

    op.create_table(
        "story_universe_links",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_story_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_story_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("shared_entities", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("shared_themes", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_story_id", "target_story_id", name="uq_story_link"),
    )


def downgrade() -> None:
    op.drop_table("story_universe_links")
    op.drop_table("universe_cluster_memberships")
    op.drop_table("universe_clusters")
    op.drop_table("story_themes")
    op.drop_table("story_entities")
    op.drop_table("story_corpora")
