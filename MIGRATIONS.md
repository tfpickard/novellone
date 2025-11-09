# Database Migrations

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations.

## Automatic Migrations (Recommended)

When using Docker Compose, migrations run automatically via the `migrate` service:

```bash
# Development
docker compose up

# Production
docker compose -f docker-compose.prod.yml up
```

The `migrate` service:
- Runs once when you start the stack
- Waits for the database to be healthy
- Applies all pending migrations
- Exits with success/failure status
- Backend only starts if migrations succeed

## Manual Migration Commands

### Run migrations manually (if needed)

If you need to run migrations manually or the automatic migration fails:

```bash
# Using docker compose (recommended)
docker compose run --rm migrate

# Or run directly in a one-off container
docker compose -f docker-compose.prod.yml run --rm migrate
```

### Run migrations without Docker

If you have Python and the dependencies installed locally:

```bash
cd backend
export DATABASE_URL="postgresql://storyuser:password@localhost:5432/stories"
python migrate.py
```

### View migration status

```bash
# In the backend container
docker compose exec backend alembic current

# Or locally
cd backend
alembic current
```

### Create a new migration

After modifying models in `backend/models.py`:

```bash
cd backend

# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Or create empty migration to write manually
alembic revision -m "description of changes"
```

Edit the generated file in `backend/alembic/versions/` and implement `upgrade()` and `downgrade()`.

## Migration Files

Migrations are stored in `backend/alembic/versions/`:

- `0001_initial_schema.py` - Initial database schema
- `0002_add_system_config.py` - System configuration table
- `0003_add_cover_image_url.py` - Cover image support
- `0004_add_chaos_parameters.py` - Story chaos parameters
- `0005_add_style_metadata.py` - Author styles and metadata

## Troubleshooting

### Migration container exits immediately

Check the logs:
```bash
docker compose logs migrate
```

### Database connection errors

Ensure `.env.production` has correct database credentials:
```env
DATABASE_URL=postgresql+asyncpg://storyuser:${DB_PASSWORD}@db:5432/stories
POSTGRES_USER=storyuser
POSTGRES_PASSWORD=your_secure_password
```

### Reset database (DANGER: deletes all data)

```bash
# Stop all containers
docker compose down

# Remove the database volume
docker volume rm novellone_pgdata

# Start fresh (migrations will run automatically)
docker compose up
```

### Rollback last migration

```bash
docker compose exec backend alembic downgrade -1
```

### View migration history

```bash
docker compose exec backend alembic history --verbose
```

## Production Deployment

When deploying updates with new migrations:

1. Pull the latest code
2. Rebuild containers: `docker compose -f docker-compose.prod.yml build`
3. Start stack: `docker compose -f docker-compose.prod.yml up -d`
4. Migrations run automatically before backend starts
5. Check migration logs: `docker compose -f docker-compose.prod.yml logs migrate`

The backend will not start until migrations complete successfully, ensuring database schema is always in sync with the code.
