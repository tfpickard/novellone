from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0008_story_summary_and_quality"
down_revision = "0007_meta_analysis_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("context_summary", sa.Text(), nullable=True))
    op.add_column("stories", sa.Column("context_summary_updated_at", sa.DateTime(), nullable=True))
    op.add_column("stories", sa.Column("context_summary_chapter", sa.Integer(), nullable=True))
    op.add_column("stories", sa.Column("quality_score_average", sa.Float(), nullable=True))
    op.add_column(
        "stories",
        sa.Column(
            "quality_score_samples",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("stories", "quality_score_samples")
    op.drop_column("stories", "quality_score_average")
    op.drop_column("stories", "context_summary_chapter")
    op.drop_column("stories", "context_summary_updated_at")
    op.drop_column("stories", "context_summary")
