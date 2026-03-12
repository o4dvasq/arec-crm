"""
Admin routes for AREC CRM — user management, config.

All routes require admin role.
"""

from flask import Blueprint, render_template, request, jsonify, g
from auth.decorators import require_admin
from db import get_session
from models import User
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
@require_admin
def users():
    """Admin page: list users, change roles."""
    db_session = get_session()
    try:
        users = db_session.query(User).order_by(User.created_at.desc()).all()
        user_list = [
            {
                'id': u.id,
                'display_name': u.display_name,
                'email': u.email,
                'role': u.role,
                'last_login': u.last_login.strftime('%b %d') if u.last_login else 'Never',
                'last_login_full': u.last_login.isoformat() if u.last_login else None,
                'is_current_user': u.id == g.user.get('id')
            }
            for u in users
        ]
        return render_template('admin/users.html', users=user_list)
    finally:
        db_session.close()


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@require_admin
def update_user_role(user_id):
    """Update a user's role (admin or user)."""
    # Prevent self-demotion
    if user_id == g.user.get('id'):
        return jsonify({'error': 'Cannot change your own role'}), 403

    data = request.get_json()
    new_role = data.get('role')

    if new_role not in ['admin', 'user']:
        return jsonify({'error': 'Invalid role. Must be admin or user.'}), 400

    db_session = get_session()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.role = new_role
        db_session.commit()

        return jsonify({
            'success': True,
            'user_id': user.id,
            'role': user.role
        })
    finally:
        db_session.close()
