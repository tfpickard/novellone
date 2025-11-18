"""Empty compatibility migration for missing content controls revision."""

from __future__ import annotations

from alembic import op  # noqa: F401  (required for Alembic runtime discovery)


# revision identifiers, used by Alembic.
revision = "0008_add_content_controls"
down_revision = "0007_meta_analysis_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Previously added content control fields (already present)."""
    # This project historically included a migration named
    # ``0008_add_content_controls`` that introduced the content-control
    # configuration columns. Some deployed databases have this revision
    # recorded even though the file is missing from the repository.  We
    # keep this placeholder migration so Alembic can resolve the history
    # chain without re-applying schema changes.
    pass


def downgrade() -> None:
    # No-op placeholder.
    pass
