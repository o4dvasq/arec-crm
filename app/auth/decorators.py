"""decorators.py — Auth decorators for Flask routes."""

from functools import wraps


def require_api_key_or_login(f):
    """No-op for local dev. Auth bypassed."""
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated
