#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn server on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"

