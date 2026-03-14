#!/bin/bash
# Azure App Service startup script for AREC CRM
# Dependencies are installed by Oryx during deployment (SCM_DO_BUILD_DURING_DEPLOYMENT=true)
# This script handles DB checks, auto-migrate, and gunicorn startup

set -x

echo "Starting AREC CRM on Azure App Service..."
cd /home/site/wwwroot

# Activate Oryx-built virtual environment if present
if [ -f /home/site/wwwroot/antenv/bin/activate ]; then
    echo "Activating Oryx virtual environment..."
    source /home/site/wwwroot/antenv/bin/activate
fi

# Install/sync dependencies into the active environment.
# Oryx may not rebuild the venv on every deploy (missing oryx-manifest.toml),
# so we ensure packages are always current before starting.
echo "Installing dependencies from app/requirements.txt..."
pip install --no-cache-dir -r /home/site/wwwroot/app/requirements.txt

# Check if database needs initialization (first deploy only)
echo "Checking database status..."
DB_INITIALIZED=$(python3 -c "
import os
import sys
sys.path.insert(0, '/home/site/wwwroot/app')
from dotenv import load_dotenv
load_dotenv()
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(os.environ.get('DATABASE_URL'))
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM organizations'))
        count = result.scalar()
        print('initialized' if count >= 0 else 'empty')
except Exception as e:
    print('uninitialized')
" 2>/dev/null)

if [ "$DB_INITIALIZED" != "initialized" ]; then
    echo "Database not initialized. Running initialization scripts..."
    echo "Step 1: Creating schema..."
    python3 scripts/create_schema.py
    if [ $? -ne 0 ]; then
        echo "ERROR: Schema creation failed. Starting app anyway to show error page."
    else
        echo "Step 2: Migrating data..."
        python3 scripts/migrate_to_postgres.py
        if [ $? -eq 0 ]; then
            echo "Database initialized successfully"
        else
            echo "ERROR: Migration failed. App may not work correctly."
        fi
    fi
else
    echo "Database already initialized (found organizations table with data)"
fi

# Run auto-migrate to sync schema from models
echo "Running auto-migrate..."
python3 -c "
import sys
sys.path.insert(0, '/home/site/wwwroot/app')
from dotenv import load_dotenv
load_dotenv()
from db import init_db
from auto_migrate import auto_migrate
try:
    engine = init_db()
    auto_migrate(engine)
    print('Auto-migrate complete.')
except Exception as e:
    print(f'ERROR: Auto-migrate failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "ERROR: Auto-migrate failed. Continuing anyway..."
fi

# Start gunicorn
echo "Starting Gunicorn..."
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
PORT=${PORT:-8000}
echo "Binding to port $PORT"

exec gunicorn \
    --bind=0.0.0.0:$PORT \
    --workers=4 \
    --timeout=120 \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=info \
    app.delivery.dashboard:app
