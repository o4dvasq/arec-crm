#!/bin/bash
# Azure App Service startup script for AREC CRM
# This runs when the container starts on Azure App Service

echo "Starting AREC CRM on Azure App Service..."

# Navigate to app directory
cd /home/site/wwwroot/app

# Run database migrations (idempotent schema creation)
# Note: Only needed on first deploy or schema changes
# python3 /home/site/wwwroot/scripts/create_schema.py

# Start gunicorn with 4 workers
echo "Starting Gunicorn..."
exec gunicorn \
    --bind=0.0.0.0:8000 \
    --workers=4 \
    --timeout=120 \
    --access-logfile=- \
    --error-logfile=- \
    delivery.dashboard:app
