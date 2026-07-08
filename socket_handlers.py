"""Socket.IO handlers — real-time dashboard updates.

Security: a client may only join room `form_{id}` if they are the form owner.
The submit endpoint (respond.py) emits `new_response` into that room; the
dashboard client picks it up and refreshes charts without reloading.
"""
from flask import request
from flask_login import current_user
from models import Form
from extensions import socketio


@socketio.on("connect")
def on_connect():
    # reject if we cannot establish Flask-Login context (shouldn't happen)
    pass


@socketio.on("join_form")
def on_join_form(data):
    """Client asks to join room `form_{id}`.

    Only the form owner is allowed. Anyone else is silently rejected
    (we don't even tell them why — no information leak).
    """
    form_id = data.get("form_id") if isinstance(data, dict) else None
    if form_id is None:
        return {"ok": False, "error": "missing_form_id"}

    try:
        form_id = int(form_id)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_form_id"}

    if not current_user.is_authenticated:
        return {"ok": False, "error": "auth_required"}

    form = Form.query.filter_by(id=form_id, user_id=current_user.id).first()
    if form is None:
        return {"ok": False, "error": "not_owner"}

    from flask import request as flask_request
    from flask_socketio import join_room
    join_room(f"form_{form_id}")
    return {"ok": True, "room": f"form_{form_id}"}


@socketio.on("leave_form")
def on_leave_form(data):
    from flask_socketio import leave_room
    form_id = data.get("form_id") if isinstance(data, dict) else None
    if form_id is None:
        return {"ok": False}
    try:
        form_id = int(form_id)
    except (TypeError, ValueError):
        return {"ok": False}
    leave_room(f"form_{form_id}")
    return {"ok": True}
