"""add cover_image_url to stories

Revision ID: 0003
Revises: 0002
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('stories', sa.Column('cover_image_url', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column('stories', 'cover_image_url')


