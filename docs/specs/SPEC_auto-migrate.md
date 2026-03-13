# SPEC: Auto-Migrate on Startup

**Project:** arec-crm
**Date:** 2026-03-13
**Status:** Ready for implementation
**Priority:** High (infrastructure — unblocks all future schema changes)

---

## 1. Objective

Eliminate manual database migration steps by automatically applying schema changes on every deploy. When a developer adds a column to `models.py`, the next push to `azure-migration` deploys the code AND the schema change lands in Postgres automatically — no manual scripts, no psql sessions, no DBA work.

## 2. Scope

**In scope:**
- New file `app/auto_migrate.py` that compares SQLAlchemy models against the live database and applies additive changes
- Hook into `startup.sh` to run auto-migrate on every Azure deploy
- Hook into `dashboard.py` to run auto-migrate on local dev startup
- Support for: adding new columns, adding new tables, adding new indexes
- Logging of every migration action taken
- Safe no-op when schema is already current

**Out of scope:**
- Column renames (rare, handle manually when needed)
- Column deletions / type changes (destructive — always manual)
- Data migrations (backfilling values, transforming data)
- Alembic or any third-party migration framework
- Rollback capability

## 3. Business Rules

- **Additive only.** Auto-migrate will ADD columns, tables, and indexes. It will NEVER drop, rename, or alter existing columns. This is a safety constraint — destructive changes require a manual migration script.
- **Idempotent.** Running auto-migrate 10 times in a row produces the same result as running it once. Uses `IF NOT EXISTS` for all DDL.
- **Models are the source of truth.** The SQLAlchemy models in `models.py` define what the schema SHOULD look like. Auto-migrate diffs the models against the actual database and applies the missing pieces.
- **Runs before the app serves traffic.** On Azure, it runs in `startup.sh` before gunicorn starts. Locally, it runs during `init_db()` or app factory setup.
- **Fails loud, doesn't block.** If a migration fails (e.g., permission error), log the error clearly but still start the app. The app may partially work, and the logs will show what needs manual attention.

## 4. Data Model / Schema Changes

None — this spec IS the schema change mechanism.

## 5. Technical Design

### `app/auto_migrate.py`

Core function: `auto_migrate(engine)`

```python
"""
Auto-migrate: compare SQLAlchemy models against live DB, apply additive changes.

Only handles:
  - New tables (CREATE TABLE IF NOT EXISTS)
  - New columns (ALTER TABLE ADD COLUMN IF NOT EXISTS)
  - New indexes (CREATE INDEX IF NOT EXISTS)

Never handles:
  - Column renames, type changes, or deletions
  - Data migrations
"""

from sqlalchemy import inspect, text
from app.models import Base
import logging

log = logging.getLogger(__name__)

def auto_migrate(engine):
    """Compare models to live schema, apply additive DDL."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                # New table — create it
                log.info(f"[auto-migrate] Creating table: {table_name}")
                table.create(engine, checkfirst=True)
                continue

            # Table exists — check for missing columns
            existing_cols = {c['name'] for c in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name not in existing_cols:
                    col_type = column.type.compile(engine.dialect)
                    nullable = "NULL" if column.nullable else "NOT NULL"
                    default = ""
                    if column.default is not None and column.default.is_scalar:
                        default = f"DEFAULT {column.default.arg!r}"

                    sql = f'ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS "{column.name}" {col_type} {nullable} {default}'
                    log.info(f"[auto-migrate] Adding column: {table_name}.{column.name}")
                    conn.execute(text(sql.strip()))

            # Check for missing indexes
            existing_indexes = {idx['name'] for idx in inspector.get_indexes(table_name) if idx['name']}
            for index in table.indexes:
                if index.name and index.name not in existing_indexes:
                    log.info(f"[auto-migrate] Creating index: {index.name}")
                    try:
                        index.create(engine)
                    except Exception as e:
                        log.warning(f"[auto-migrate] Index {index.name} failed: {e}")

    log.info("[auto-migrate] Schema sync complete.")
```

NOTE: The above is illustrative pseudocode for the spec. The implementing agent should handle edge cases around column type compilation (especially Enums, JSON/JSONB, BigInteger), and test against both PostgreSQL and SQLite (for test suite compatibility).

### Integration Point 1: `startup.sh`

Add auto-migrate step after the DB initialization check, before gunicorn starts:

```bash
# After the existing DB initialization block, before gunicorn:
echo "Running auto-migrate..."
python3 -c "
import sys
sys.path.insert(0, '/home/site/wwwroot/app')
from dotenv import load_dotenv
load_dotenv()
from db import init_db
from auto_migrate import auto_migrate
engine = init_db()
auto_migrate(engine)
print('Auto-migrate complete.')
"
```

### Integration Point 2: `dashboard.py` (local dev)

After `db.init_app(app)`, call auto-migrate:

```python
from app.auto_migrate import auto_migrate
from app.db import engine

db.init_app(app)
auto_migrate(engine)  # Sync schema on local startup
```

### Integration Point 3: `conftest.py` (tests)

Tests use SQLite in-memory and `Base.metadata.create_all(engine)`, which already creates all tables from models. No change needed — auto-migrate is not needed in tests since `create_all` handles it.

## 6. Integration Points

- Reads from: `app/models.py` (SQLAlchemy model definitions)
- Reads from: live PostgreSQL database (via `sqlalchemy.inspect`)
- Called by: `startup.sh` (Azure deploy), `dashboard.py` (local dev)
- Logs to: stdout (captured by Azure App Service logs and local terminal)

## 7. Constraints

- **PostgreSQL `ADD COLUMN IF NOT EXISTS` requires Postgres 9.6+.** Azure Flexible Server is 16.x, so this is fine.
- **SQLite does NOT support `IF NOT EXISTS` on `ALTER TABLE`.** The auto-migrate function should detect the dialect and skip column-add logic for SQLite (tests use `create_all` anyway).
- **Enum columns need special handling.** PostgreSQL requires `CREATE TYPE ... AS ENUM` before the column can use it. SQLAlchemy's `Enum` type handles this via `create_type=True` in `checkfirst` mode, but the auto-migrate function should handle the case where the enum type exists but the column doesn't.
- **JSON vs JSONB.** Models may use `JSON` (SQLAlchemy generic) which maps to `JSON` on Postgres. If we want `JSONB`, specify it explicitly in the model. Auto-migrate should respect whatever the model declares.
- **No concurrent migration.** Only one instance should run auto-migrate at a time. On Azure with 4 gunicorn workers, only `startup.sh` runs it (before workers spawn). Locally, it runs once during app factory.
- **Imports must work from both `startup.sh` (standalone) and `dashboard.py` (Flask context).** The function takes an `engine` parameter, not a Flask app.

## 8. Acceptance Criteria

- [ ] New file `app/auto_migrate.py` exists with `auto_migrate(engine)` function
- [ ] Adding a new column to `models.py` and restarting the app creates that column in the database automatically
- [ ] Adding a new table to `models.py` and restarting creates the table automatically
- [ ] Running auto-migrate when schema is already current produces no errors and no DDL
- [ ] Auto-migrate logs each action taken (table created, column added, index created)
- [ ] Auto-migrate does NOT drop, rename, or alter existing columns
- [ ] Auto-migrate handles PostgreSQL dialect (production) correctly
- [ ] Auto-migrate skips column-add logic gracefully on SQLite (test suite)
- [ ] `startup.sh` calls auto-migrate before gunicorn starts
- [ ] `dashboard.py` calls auto-migrate during local dev startup
- [ ] All 99+ existing tests still pass
- [ ] Manual migration scripts (`scripts/migrate_add_*.py`) can be retired going forward (but left in place for historical reference)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/auto_migrate.py` | **New file** — core auto-migrate logic |
| `startup.sh` | Add auto-migrate call before gunicorn |
| `app/delivery/dashboard.py` | Add auto-migrate call during app factory |
| `app/models.py` | No changes needed — this is the source of truth that auto-migrate reads |
| `app/tests/test_auto_migrate.py` | **New file** — tests for auto-migrate logic |
