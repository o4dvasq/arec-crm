#!/bin/bash

echo "=== AREC CRM Startup ==="

# Resolve the app root — Oryx may extract to a temp dir, not /home/site/wwwroot
# Try multiple strategies to find where our code lives
if [ -f "$(dirname "$0")/app/delivery/dashboard.py" ]; then
    APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
elif [ -f "/home/site/wwwroot/app/delivery/dashboard.py" ]; then
    APP_ROOT="/home/site/wwwroot"
else
    # Search common Oryx temp extraction dirs
    APP_ROOT=$(find /tmp -maxdepth 2 -name "dashboard.py" -path "*/delivery/*" 2>/dev/null | head -1 | sed 's|/app/delivery/dashboard.py||')
    if [ -z "$APP_ROOT" ]; then
        echo "FATAL: Cannot find app root"
        exit 1
    fi
fi
echo "App root: $APP_ROOT"

# Activate virtual environment if available (don't fail if missing)
for VENV_PATH in "$APP_ROOT/antenv" "/home/site/wwwroot/antenv"; do
    if [ -f "$VENV_PATH/bin/activate" ]; then
        echo "Activating venv: $VENV_PATH"
        source "$VENV_PATH/bin/activate" || true
        break
    fi
done

# Ensure dependencies are current
echo "Installing/syncing dependencies..."
pip install -r "$APP_ROOT/app/requirements.txt" --quiet 2>&1 | tail -5 || true

# Run auto-migrate (additive-only DDL — safe to run every boot)
echo "Running auto-migrate..."
cd "$APP_ROOT"
PYTHONPATH="$APP_ROOT/app" python3 -c "
import db as db_module
from auto_migrate import auto_migrate
db_module.init_db()
auto_migrate(db_module.engine)
print('Auto-migrate complete.')
" || echo "WARNING: auto-migrate failed, continuing anyway"

# Start gunicorn
echo "Starting gunicorn on port ${PORT:-8000}..."
cd "$APP_ROOT/app"
exec gunicorn delivery.dashboard:app \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
