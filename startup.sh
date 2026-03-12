#!/bin/bash
# Azure App Service startup script for AREC CRM
# This runs when the container starts on Azure App Service

set -x  # Enable debug output

echo "Starting AREC CRM on Azure App Service..."

# Navigate to project root
cd /home/site/wwwroot

# Check if database needs initialization
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
            echo "✓ Database initialized successfully"
        else
            echo "ERROR: Migration failed. App may not work correctly."
        fi
    fi
else
    echo "✓ Database already initialized (found organizations table with data)"
fi

# Install dependencies if not already installed
echo "Checking Python dependencies..."
if [ ! -f "/home/site/wwwroot/.deps_installed" ]; then
    echo "Installing dependencies from app/requirements.txt..."
    python3 -m pip install --no-cache-dir -r /home/site/wwwroot/app/requirements.txt
    if [ $? -eq 0 ]; then
        touch /home/site/wwwroot/.deps_installed
        echo "✓ Dependencies installed successfully"
    else
        echo "ERROR: Failed to install dependencies"
        exit 1
    fi
else
    echo "✓ Dependencies already installed"
fi

# Start gunicorn with 4 workers
echo "Starting Gunicorn..."
cd /home/site/wwwroot
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
exec gunicorn \
    --bind=0.0.0.0:8000 \
    --workers=4 \
    --timeout=120 \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=debug \
    app.delivery.dashboard:app
