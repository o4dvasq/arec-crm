#!/bin/bash
# Azure database initialization script
# Run this from the wwwroot directory on Azure App Service

cd /home/site/wwwroot

echo "Step 1: Creating database schema..."
python3 scripts/create_schema.py
if [ $? -ne 0 ]; then
    echo "ERROR: Schema creation failed"
    exit 1
fi

echo "Step 2: Migrating data from markdown to PostgreSQL..."
python3 scripts/migrate_to_postgres.py
if [ $? -ne 0 ]; then
    echo "ERROR: Migration failed"
    exit 1
fi

echo "Step 3: Verifying migration..."
python3 scripts/verify_migration.py
if [ $? -ne 0 ]; then
    echo "WARNING: Verification found issues"
fi

echo "Database initialization complete!"
