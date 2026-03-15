#!/usr/bin/env bash
# Kill any running CRM server and restart it.
# Usage: bash dev.sh

lsof -ti :8000 | xargs -r kill -9 2>/dev/null
sleep 0.5
cd "$(dirname "$0")"
python3 app/delivery/dashboard.py
