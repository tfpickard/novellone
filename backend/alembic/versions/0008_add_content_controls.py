"""add content controls columns

Revision ID: 0008
Revises: 0007
Create Date: 2025-01-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column(
            "content_settings",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "chapters",
        sa.Column(
            "content_levels",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("stories", "content_settings", server_default=None)
    op.alter_column("chapters", "content_levels", server_default=None)


def downgrade() -> None:
    op.drop_column("chapters", "content_levels")
    op.drop_column("stories", "content_settings")
