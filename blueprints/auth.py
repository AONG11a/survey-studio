"""Authentication blueprint: register, login, logout.

Passwords are hashed with Werkzeug's scrypt. Sessions via Flask-Login.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from extensions import limiter
import re

auth_bp = Blueprint("auth", __name__)

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("builder.my_forms"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        errors = []
        if not _USERNAME_RE.match(username):
            errors.append("ชื่อผู้ใช้ต้องเป็น A-Z a-z 0-9 _ และยาว 3-30 ตัวอักษร")
        if not _EMAIL_RE.match(email):
            errors.append("รูปแบบอีเมลไม่ถูกต้อง")
        if len(password) < 6:
            errors.append("รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร")
        if password != confirm:
            errors.append("รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน")
        if User.query.filter_by(username=username).first():
            errors.append("ชื่อผู้ใช้นี้ถูกใช้แล้ว")
        if User.query.filter_by(email=email).first():
            errors.append("อีเมลนี้ถูกใช้แล้ว")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "register.html", username=username, email=email
            )

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("สมัครสมาชิกสำเร็จ ยินดีต้อนรับ!", "success")
        return redirect(url_for("builder.my_forms"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute; 50 per hour", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("builder.my_forms"))

    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        user = None
        if _EMAIL_RE.match(identifier):
            user = User.query.filter_by(email=identifier.lower()).first()
        else:
            user = User.query.filter_by(username=identifier).first()

        if user is None or not user.check_password(password):
            flash("ชื่อผู้ใช้/อีเมล หรือรหัสผ่านไม่ถูกต้อง", "danger")
            return render_template("login.html", identifier=identifier)

        login_user(user, remember=remember)
        flash("เข้าสู่ระบบสำเร็จ", "success")
        nxt = request.args.get("next")
        # avoid open redirect
        if nxt and nxt.startswith("/"):
            return redirect(nxt)
        return redirect(url_for("builder.my_forms"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ออกจากระบบแล้ว", "info")
    return redirect(url_for("auth.login"))
