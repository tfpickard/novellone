"""add summary and cover art fields

Revision ID: 0002_add_story_cover_art
Revises: 0001_initial_schema
Create Date: 2025-02-15 00:00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_add_story_cover_art"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("stories", sa.Column("cover_art_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("stories", "cover_art_url")
    op.drop_column("stories", "summary")
