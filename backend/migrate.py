#!/usr/bin/env python3
"""
Standalone migration runner script.
Runs Alembic migrations without starting the main application.
Can be used as a one-off container or run directly.
"""
import os
import sys
from alembic import command
from alembic.config import Config


def run_migrations():
    """Run all pending migrations."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Create Alembic config
    alembic_cfg = Config(os.path.join(script_dir, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(script_dir, "alembic"))

    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    # For Alembic, we need to use the sync driver (psycopg2)
    # Replace asyncpg with psycopg2
    database_url = database_url.replace("+asyncpg", "")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    print(f"Running migrations to database: {database_url.split('@')[1] if '@' in database_url else 'database'}")

    try:
        # Run migrations to head
        command.upgrade(alembic_cfg, "head")
        print("✓ Migrations completed successfully")
        return 0
    except Exception as e:
        print(f"✗ Migration failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_migrations())
