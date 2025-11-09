#!/usr/bin/env python3
"""
Fix migration state by resetting to 0004 (non-interactive).
Run this if you see "Can't locate revision identified by '0006'" error.
"""
import os
import sys
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def fix_migration_state():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1

    print(f"Connecting to database...")
    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Check if alembic_version table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'alembic_version'
                )
            """))
            table_exists = result.scalar()

            if not table_exists:
                print("✓ No alembic_version table - will be created on first migration")
                return 0

            # Get current version
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()

            print(f"Current database version: {current_version}")

            # If it's an invalid version (like 0006), reset to 0004
            if current_version not in ['0001', '0002', '0003', '0004', '0005']:
                print(f"Invalid version {current_version} detected - resetting to 0004")
                await conn.execute(text("UPDATE alembic_version SET version_num = '0004'"))
                print("✓ Reset to version 0004")
                print("  Migration 0005 will now be applied")
                return 0
            else:
                print(f"✓ Version {current_version} is valid - no fix needed")
                return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(fix_migration_state()))
