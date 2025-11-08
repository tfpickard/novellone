"""add chaos parameters to stories and chapters

Revision ID: 0004
Revises: 0003
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add chaos parameters to stories table
    op.add_column('stories', sa.Column('absurdity_initial', sa.Float(), nullable=False, server_default='0.1'))
    op.add_column('stories', sa.Column('surrealism_initial', sa.Float(), nullable=False, server_default='0.1'))
    op.add_column('stories', sa.Column('ridiculousness_initial', sa.Float(), nullable=False, server_default='0.1'))
    op.add_column('stories', sa.Column('insanity_initial', sa.Float(), nullable=False, server_default='0.1'))
    
    op.add_column('stories', sa.Column('absurdity_increment', sa.Float(), nullable=False, server_default='0.05'))
    op.add_column('stories', sa.Column('surrealism_increment', sa.Float(), nullable=False, server_default='0.05'))
    op.add_column('stories', sa.Column('ridiculousness_increment', sa.Float(), nullable=False, server_default='0.05'))
    op.add_column('stories', sa.Column('insanity_increment', sa.Float(), nullable=False, server_default='0.05'))
    
    # Add chaos parameters to chapters table (nullable as they're set by OpenAI)
    op.add_column('chapters', sa.Column('absurdity', sa.Float(), nullable=True))
    op.add_column('chapters', sa.Column('surrealism', sa.Float(), nullable=True))
    op.add_column('chapters', sa.Column('ridiculousness', sa.Float(), nullable=True))
    op.add_column('chapters', sa.Column('insanity', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove chaos parameters from chapters table
    op.drop_column('chapters', 'insanity')
    op.drop_column('chapters', 'ridiculousness')
    op.drop_column('chapters', 'surrealism')
    op.drop_column('chapters', 'absurdity')
    
    # Remove chaos parameters from stories table
    op.drop_column('stories', 'insanity_increment')
    op.drop_column('stories', 'ridiculousness_increment')
    op.drop_column('stories', 'surrealism_increment')
    op.drop_column('stories', 'absurdity_increment')
    
    op.drop_column('stories', 'insanity_initial')
    op.drop_column('stories', 'ridiculousness_initial')
    op.drop_column('stories', 'surrealism_initial')
    op.drop_column('stories', 'absurdity_initial')

