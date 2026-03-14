#!/bin/bash
set -e

echo "=== AREC CRM Startup ==="

# Activate Oryx virtual environment
if [ -d "/home/site/wwwroot/antenv" ]; then
    echo "Activating virtual environment..."
    source /home/site/wwwroot/antenv/bin/activate
fi

# Ensure dependencies are current (handles stale antenv after code deploy)
echo "Installing/syncing dependencies..."
pip install -r /home/site/wwwroot/app/requirements.txt --quiet 2>&1 | tail -5

# Run auto-migrate (additive-only DDL — safe to run every boot)
echo "Running auto-migrate..."
cd /home/site/wwwroot
PYTHONPATH=/home/site/wwwroot/app python3 -c "
import db as db_module
from auto_migrate import auto_migrate
db_module.init_db()
auto_migrate(db_module.engine)
print('Auto-migrate complete.')
"

# Start gunicorn
echo "Starting gunicorn on port ${PORT:-8000}..."
cd /home/site/wwwroot/app
exec gunicorn delivery.dashboard:app \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
