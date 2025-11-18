"""Backfill and enforce chapter content level metadata"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "0010_add_chapter_content_levels"
down_revision = "0009_story_summary_and_quality"
branch_labels = None
depends_on = None


def _has_column(inspector: Inspector, table_name: str, column_name: str) -> bool:
    columns = inspector.get_columns(table_name)
    return any(col["name"] == column_name for col in columns)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    column_type = postgresql.JSONB(astext_type=sa.Text())

    if not _has_column(inspector, "chapters", "content_levels"):
        op.add_column(
            "chapters",
            sa.Column(
                "content_levels",
                column_type,
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
    else:
        op.alter_column(
            "chapters",
            "content_levels",
            existing_type=column_type,
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        )

    op.execute("UPDATE chapters SET content_levels = '{}'::jsonb WHERE content_levels IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "chapters", "content_levels"):
        op.drop_column("chapters", "content_levels")
