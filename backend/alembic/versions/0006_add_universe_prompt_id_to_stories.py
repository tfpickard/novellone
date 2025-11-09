"""add universe_prompt_id to stories

Revision ID: 0006
Revises: 0005
Create Date: 2025-11-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add universe_prompt_id column to stories table
    op.add_column('stories', sa.Column('universe_prompt_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_stories_universe_prompt_id',
        'stories',
        'universe_prompts',
        ['universe_prompt_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove universe_prompt_id column from stories table
    op.drop_constraint('fk_stories_universe_prompt_id', 'stories', type_='foreignkey')
    op.drop_column('stories', 'universe_prompt_id')
