"""add universe prompt, universe element, and cohesion metric tables

Revision ID: 0005
Revises: 0004
Create Date: 2025-11-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create universe_prompts table
    op.create_table(
        'universe_prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('characters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('themes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('lore', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('narrative_constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('character_weight', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('setting_weight', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('theme_weight', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('lore_weight', sa.Float(), nullable=False, server_default='0.5'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_universe_prompts_created_at'), 'universe_prompts', ['created_at'], unique=False)

    # Create universe_elements table
    op.create_table(
        'universe_elements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('universe_prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_story_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('element_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extracted_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['universe_prompt_id'], ['universe_prompts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_universe_elements_element_type'), 'universe_elements', ['element_type'], unique=False)

    # Create cohesion_metrics table
    op.create_table(
        'cohesion_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('story_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('universe_prompt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('character_recurrence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('thematic_overlap_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('timeline_continuity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('overall_cohesion_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['universe_prompt_id'], ['universe_prompts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cohesion_metrics_calculated_at'), 'cohesion_metrics', ['calculated_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (to respect foreign keys)
    op.drop_index(op.f('ix_cohesion_metrics_calculated_at'), table_name='cohesion_metrics')
    op.drop_table('cohesion_metrics')

    op.drop_index(op.f('ix_universe_elements_element_type'), table_name='universe_elements')
    op.drop_table('universe_elements')

    op.drop_index(op.f('ix_universe_prompts_created_at'), table_name='universe_prompts')
    op.drop_table('universe_prompts')
