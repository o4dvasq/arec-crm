"""
Flask app — AREC CRM multi-user platform (port 8000).

Blueprint modules:
  - crm_blueprint.py  → /crm routes
"""

import os
import sys

# Allow imports from app/
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Load .env from app/ directory
from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, ".env"))

from flask import Flask, redirect, url_for

from delivery.crm_blueprint import crm_bp
from delivery.admin_blueprint import admin_bp
from db import init_app
from auth.entra_auth import init_auth_routes

PROJECT_ROOT = os.path.dirname(APP_DIR)

app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)

# Set Flask secret key for session management
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(32).hex())

# Initialize database
init_app(app)

# Initialize authentication routes (logs DEV_USER warning if set)
init_auth_routes(app)

# Register blueprints
app.register_blueprint(crm_bp)
app.register_blueprint(admin_bp)


# ---------------------------------------------------------------------------
# Root route — redirect to CRM
# ---------------------------------------------------------------------------

@app.route('/')
def dashboard():
    """Root route redirects to CRM pipeline."""
    return redirect(url_for('crm.pipeline'))




if __name__ == '__main__':
    port = int(os.environ.get("DASHBOARD_PORT", "8000"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
