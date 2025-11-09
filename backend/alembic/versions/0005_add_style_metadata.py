"""add style authors and additional metadata

Revision ID: 0005
Revises: 0004
Create Date: 2025-11-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add style and metadata fields to stories table
    op.add_column('stories', sa.Column('style_authors', JSONB, nullable=True))
    op.add_column('stories', sa.Column('narrative_perspective', sa.String(100), nullable=True))
    op.add_column('stories', sa.Column('tone', sa.String(100), nullable=True))
    op.add_column('stories', sa.Column('genre_tags', JSONB, nullable=True))
    op.add_column('stories', sa.Column('estimated_reading_time_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove style and metadata fields from stories table
    op.drop_column('stories', 'estimated_reading_time_minutes')
    op.drop_column('stories', 'genre_tags')
    op.drop_column('stories', 'tone')
    op.drop_column('stories', 'narrative_perspective')
    op.drop_column('stories', 'style_authors')
