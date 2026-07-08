"""App factory + blueprint registration + Socket.IO init.

Run with:  python app.py
First run auto-creates survey.db.
"""
import os
from urllib.parse import urlparse
from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from models import db, User
from extensions import socketio, login_manager, csrf, limiter


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(uid):
        try:
            return db.session.get(User, int(uid))
        except (TypeError, ValueError):
            return None

    # ---- Blueprints ---------------------------------------------------------
    from blueprints.auth import auth_bp
    from blueprints.builder import builder_bp
    from blueprints.respond import respond_bp
    from blueprints.dashboard import dashboard_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(builder_bp)
    app.register_blueprint(respond_bp)
    app.register_blueprint(dashboard_bp)

    # The public submit endpoint is used by anonymous respondents who have no
    # authenticated session to protect; exempt it from CSRF (it is otherwise
    # validated field-by-field on the server).
    csrf.exempt(respond_bp)

    # ---- Socket.IO handlers -----------------------------------------------
    from importlib import import_module
    import_module("socket_handlers")

    # ---- Security headers ---------------------------------------------------
    @app.after_request
    def set_security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    # ---- Root route --------------------------------------------------------
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("builder.my_forms"))
        return redirect(url_for("auth.login"))

    # ---- Error handlers ----------------------------------------------------
    def _wants_json():
        return request.path.startswith("/api/") or request.is_json

    @app.errorhandler(400)
    def bad_request(e):
        if _wants_json():
            return jsonify({"error": "bad_request"}), 400
        return render_template("error.html", code=400, message="คำขอไม่ถูกต้อง"), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if _wants_json():
            return jsonify({"error": "auth_required"}), 401
        return redirect(url_for("auth.login"))

    @app.errorhandler(403)
    def forbidden(e):
        if _wants_json():
            return jsonify({"error": "forbidden"}), 403
        return render_template("error.html", code=403, message="ไม่มีสิทธิ์เข้าถึง"), 403

    @app.errorhandler(404)
    def not_found(e):
        if _wants_json():
            return jsonify({"error": "not_found"}), 404
        return render_template("error.html", code=404, message="ไม่พบหน้าที่ค้นหา"), 404

    @app.errorhandler(413)
    def too_large(e):
        if _wants_json():
            return jsonify({"error": "payload_too_large"}), 413
        return render_template("error.html", code=413, message="ข้อมูลใหญ่เกินไป"), 413

    @app.errorhandler(429)
    def too_many(e):
        if _wants_json():
            return jsonify({"error": "rate_limited", "detail": str(e.description)}), 429
        return render_template("error.html", code=429, message="คำขอถี่เกินไป กรุณาลองใหม่ภายหลัง"), 429

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        if _wants_json():
            return jsonify({"error": "server_error"}), 500
        return render_template("error.html", code=500, message="เกิดข้อผิดพลาดภายในระบบ"), 500

    # ---- Create tables on first run ---------------------------------------
    with app.app_context():
        db.create_all()
        # Add forms.public_id to databases created before share-link tokens.
        from models import ensure_form_public_ids
        ensure_form_public_ids()
        # Users self-register — no bootstrap admin is created automatically.

    return app


app = create_app()

# Restrict Socket.IO cross-origin to the configured base URL (plus localhost
# for development). "*" would let any website open an authenticated socket.
_origins = {Config.BASE_URL.rstrip("/")}
_parsed = urlparse(Config.BASE_URL)
if _parsed.hostname in ("localhost", "127.0.0.1") or not _parsed.hostname:
    _origins.update({
        "http://localhost:5000", "http://127.0.0.1:5000",
    })
socketio.init_app(app, cors_allowed_origins=list(_origins))


if __name__ == "__main__":
    # Cloud platforms (Render, Railway, etc.) inject the port to bind via $PORT.
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print(" Survey Platform starting at", Config.BASE_URL)
    print(" Listening on 0.0.0.0:%d" % port)
    print("=" * 60)
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        allow_unsafe_werkzeug=True,
        debug=False,
    )
