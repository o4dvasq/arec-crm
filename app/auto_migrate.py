"""
Auto-migrate: Compare SQLAlchemy models against live database, apply additive changes.

Only handles:
  - New tables (CREATE TABLE IF NOT EXISTS)
  - New columns (ALTER TABLE ADD COLUMN IF NOT EXISTS)
  - New indexes (CREATE INDEX IF NOT EXISTS)

Never handles:
  - Column renames, type changes, or deletions
  - Data migrations
  - Drops or destructive changes

This is safe to run multiple times — it is fully idempotent.
"""

import logging
from sqlalchemy import inspect, text, event
from sqlalchemy.pool import Pool

log = logging.getLogger(__name__)


def auto_migrate(engine):
    """Compare models to live schema, apply additive DDL.

    Args:
        engine: SQLAlchemy engine connected to the database.
    """
    from models import Base

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # Detect database dialect (PostgreSQL vs SQLite)
    is_sqlite = engine.dialect.name == 'sqlite'

    log.info("[auto-migrate] Starting schema sync...")

    with engine.begin() as conn:
        # First pass: Create missing tables
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                log.info(f"[auto-migrate] Creating table: {table_name}")
                try:
                    table.create(conn, checkfirst=True)
                except Exception as e:
                    log.error(f"[auto-migrate] Failed to create table {table_name}: {e}")
                    # Continue to next table rather than failing completely
                continue

        # Refresh inspector after creating new tables
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        # Second pass: Add missing columns and indexes
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue

            # Check for missing columns
            existing_cols = {c['name'] for c in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name not in existing_cols:
                    # SQLite does not support ALTER TABLE ADD COLUMN IF NOT EXISTS
                    # For SQLite, tests use Base.metadata.create_all(), so skip this
                    if is_sqlite:
                        log.debug(
                            f"[auto-migrate] Skipping column add on SQLite: "
                            f"{table_name}.{column.name} (tests use create_all)"
                        )
                        continue

                    # PostgreSQL: Add missing column
                    try:
                        col_type = column.type.compile(engine.dialect)
                        nullable = "NULL" if column.nullable else "NOT NULL"
                        default_str = ""

                        if column.default is not None:
                            if column.default.is_scalar:
                                # Scalar default (e.g., False, 'value')
                                default_arg = column.default.arg
                                if isinstance(default_arg, str):
                                    default_str = f"DEFAULT '{default_arg}'"
                                else:
                                    default_str = f"DEFAULT {default_arg}"
                            # Note: don't try to handle callable defaults in auto-migrate

                        sql = (
                            f'ALTER TABLE "{table_name}" '
                            f'ADD COLUMN IF NOT EXISTS "{column.name}" '
                            f'{col_type} {nullable} {default_str}'
                        ).strip()

                        log.info(
                            f"[auto-migrate] Adding column: {table_name}.{column.name} "
                            f"({col_type})"
                        )
                        conn.execute(text(sql))
                    except Exception as e:
                        log.error(
                            f"[auto-migrate] Failed to add column {table_name}.{column.name}: {e}"
                        )
                        # Continue rather than failing completely

            # Check for missing indexes
            try:
                existing_indexes = {
                    idx['name'] for idx in inspector.get_indexes(table_name)
                    if idx.get('name')
                }
                for index in table.indexes:
                    if index.name and index.name not in existing_indexes:
                        log.info(f"[auto-migrate] Creating index: {index.name}")
                        try:
                            index.create(engine)
                        except Exception as e:
                            log.warning(f"[auto-migrate] Index {index.name} failed: {e}")
            except Exception as e:
                log.warning(f"[auto-migrate] Failed to check indexes for {table_name}: {e}")

    log.info("[auto-migrate] Schema sync complete.")
