# Database Migration: Add demucs_command Column

## Automatic Migration

If you're starting fresh or the database is recreated, SQLAlchemy will automatically create the `demucs_command` column when the app starts.

## Manual Migration (Existing Database)

If you have an existing database with jobs data, run this migration script:

```bash
# From your host machine
docker exec -it demucs-backend python migrate_add_demucs_command.py
```

Or from inside the container:

```bash
docker exec -it demucs-backend bash
python migrate_add_demucs_command.py
```

The script will:
1. Check if the column already exists
2. Add the `demucs_command` TEXT column to the `jobs` table if needed
3. Skip if already migrated

## What This Adds

- Jobs table now has a `demucs_command` column that stores the full CLI command used
- The command is displayed in the UI when viewing completed jobs
- Old jobs without this data will not show a command (backward compatible)
