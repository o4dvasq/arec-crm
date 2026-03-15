"""conftest.py — pytest fixtures for arec-crm (markdown-local branch)."""

import os
import sys

# Add app/ to path so we can import sources.* modules
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
