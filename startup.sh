#!/bin/bash
set -e

echo "=== AREC CRM Startup ==="

# Resolve the app root (directory containing this script)
APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "App root: $APP_ROOT"

# Activate Oryx virtual environment (could be in app root or /home/site/wwwroot)
if [ -d "$APP_ROOT/antenv" ]; then
    echo "Activating virtual environment from app root..."
    source "$APP_ROOT/antenv/bin/activate"
elif [ -d "/home/site/wwwroot/antenv" ]; then
    echo "Activating virtual environment from /home/site/wwwroot..."
    source /home/site/wwwroot/antenv/bin/activate
fi

# Ensure dependencies are current (handles stale antenv after code deploy)
echo "Installing/syncing dependencies..."
pip install -r "$APP_ROOT/app/requirements.txt" --quiet 2>&1 | tail -5

# Run auto-migrate (additive-only DDL — safe to run every boot)
echo "Running auto-migrate..."
cd "$APP_ROOT"
PYTHONPATH="$APP_ROOT/app" python3 -c "
import db as db_module
from auto_migrate import auto_migrate
db_module.init_db()
auto_migrate(db_module.engine)
print('Auto-migrate complete.')
"

# Start gunicorn
echo "Starting gunicorn on port ${PORT:-8000}..."
cd "$APP_ROOT/app"
exec gunicorn delivery.dashboard:app \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
