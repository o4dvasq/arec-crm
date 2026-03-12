"""
Authentication decorators for AREC CRM.
"""

from functools import wraps
from flask import g, render_template


def require_admin(f):
    """Decorator to require admin role for a route.

    Usage:
        @app.route('/admin/users')
        @require_admin
        def admin_users():
            return "Admin page"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user:
            return render_template('access_denied.html',
                                   message="You must be logged in to access this page."), 403

        if g.user.get('role') != 'admin':
            return render_template('access_denied.html',
                                   message="You don't have permission to view this page. Contact Oscar Vasquez for access."), 403

        return f(*args, **kwargs)
    return decorated_function
