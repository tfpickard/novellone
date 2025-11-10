"""Add operational meta-analysis tables"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0007_meta_analysis_operations"
down_revision = "0006_meta_analysis_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_analysis_runs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("processed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meta_analysis_runs_started_at",
        "meta_analysis_runs",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        "ix_meta_analysis_runs_run_type",
        "meta_analysis_runs",
        ["run_type"],
        unique=False,
    )

    op.create_table(
        "story_entity_overrides",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("target_name", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_story_entity_overrides_story_id",
        "story_entity_overrides",
        ["story_id"],
        unique=False,
    )
    op.create_index(
        "ix_story_entity_overrides_action",
        "story_entity_overrides",
        ["action"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_story_entity_overrides_action", table_name="story_entity_overrides")
    op.drop_index("ix_story_entity_overrides_story_id", table_name="story_entity_overrides")
    op.drop_table("story_entity_overrides")
    op.drop_index("ix_meta_analysis_runs_run_type", table_name="meta_analysis_runs")
    op.drop_index("ix_meta_analysis_runs_started_at", table_name="meta_analysis_runs")
    op.drop_table("meta_analysis_runs")
