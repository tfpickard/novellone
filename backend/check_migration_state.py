#!/usr/bin/env python3
"""
Check and optionally fix the database migration state.
"""
import os
import sys
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def check_and_fix():
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
                print("✓ No alembic_version table exists - fresh database")
                print("  Run migrations normally with: python migrate.py")
                return 0

            # Get current version
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()

            print(f"Current database migration version: {current_version}")

            # Check if this version exists in our migration files
            valid_versions = ['0001', '0002', '0003', '0004', '0005']

            if current_version in valid_versions:
                print(f"✓ Version {current_version} is valid")
                return 0

            print(f"✗ Version {current_version} does not exist in migration files!")
            print(f"  Valid versions: {', '.join(valid_versions)}")

            # Offer to reset to last known good version
            print("\nOptions:")
            print("1. Reset to 0004 (before style metadata changes)")
            print("2. Reset to 0005 (latest)")
            print("3. Delete alembic_version table (will rerun all migrations)")
            print("4. Exit without changes")

            choice = input("\nEnter choice (1-4): ").strip()

            if choice == "1":
                await conn.execute(text("UPDATE alembic_version SET version_num = '0004'"))
                print("✓ Reset to version 0004")
                print("  Now run: python migrate.py")
                return 0
            elif choice == "2":
                await conn.execute(text("UPDATE alembic_version SET version_num = '0005'"))
                print("✓ Reset to version 0005")
                return 0
            elif choice == "3":
                await conn.execute(text("DROP TABLE alembic_version"))
                print("✓ Dropped alembic_version table")
                print("  Now run: python migrate.py")
                return 0
            else:
                print("No changes made")
                return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(check_and_fix()))
