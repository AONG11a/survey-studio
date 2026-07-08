"""Authorization helpers used across blueprints and socket handlers.

These functions are the single source of truth for ownership checks.
NEVER bypass them in any route — every user-scoped route must call one of these.
"""
from functools import wraps
from flask import abort, g
from flask_login import current_user


def owns_form(form_id, user=None):
    """Return the Form row if `user` (default: current_user) owns it, else None."""
    from models import Form
    user = user or current_user
    if not user.is_authenticated:
        return None
    return Form.query.filter_by(id=form_id, user_id=user.id).first()


def require_form_ownership(form_id):
    """404 if current_user doesn't own the form (avoids leaking existence)."""
    form = owns_form(form_id)
    if form is None:
        abort(404)
    return form


def login_required_api(f):
    """For JSON endpoints: returns 401 instead of redirecting to login page."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            from flask import jsonify
            return jsonify({"error": "auth_required"}), 401
        return f(*args, **kwargs)

    return wrapper
