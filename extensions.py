"""Shared extension instances (avoid circular imports).

Imported by app.py, models, blueprints, and socket_handlers.
"""
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# async_mode="threading" avoids the eventlet/gevent monkey-patching that breaks
# on newer Python (e.g. 3.14). Combined with the `simple-websocket` package it
# still gives real WebSocket transport. cors is tightened in app.py.
socketio = SocketIO(async_mode="threading")

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "กรุณาเข้าสู่ระบบก่อน"
login_manager.login_message_category = "warning"

csrf = CSRFProtect()

# In-memory rate limiter (fine for a single-process eventlet server).
# For multi-worker deployments point storage_uri at Redis.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)
