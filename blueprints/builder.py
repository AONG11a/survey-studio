"""Form Builder blueprint.

Owns all creator-side operations:
  - list / create / edit / delete forms
  - add / update / delete / reorder questions
  - preview, publish, QR code, share link
"""
import io
import json
import secrets
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    jsonify, abort, current_app, send_file
)
from flask_login import login_required, current_user
from models import db, Form, Question, QUESTION_TYPES
from authz import require_form_ownership, login_required_api

builder_bp = Blueprint("builder", __name__)

_QTYPE_LABELS_TH = {
    "short": "คำตอบสั้น",
    "paragraph": "ย่อหน้า",
    "multiple": "ปรนัยเลือกตอบ (Multiple choice)",
    "checkbox": "เลือกได้หลายข้อ (Checkboxes)",
    "dropdown": "ดรอปดาวน์",
    "scale": "แบบประมาณค่า (Linear scale)",
    "date": "วันที่",
    "time": "เวลา",
    "section": "แบ่งส่วน (Section)",
}


def _validate_question_payload(q):
    """Return (cleaned_dict, error_message_or_None)."""
    qtype = (q.get("type") or "").strip()
    if qtype not in QUESTION_TYPES:
        return None, f"ประเภทคำถามไม่ถูกต้อง: {qtype}"

    text = (q.get("text") or "").strip()
    if qtype != "section" and not text:
        return None, "ข้อความคำถามต้องไม่ว่าง"

    options = []
    if qtype in ("multiple", "checkbox", "dropdown"):
        options = [o.strip() for o in (q.get("options") or []) if str(o).strip()]
        if len(options) < 2:
            return None, "ตัวเลือกต้องมีอย่างน้อย 2 ตัว"

    scale_min, scale_max = 1, 5
    if qtype == "scale":
        try:
            scale_min = int(q.get("scale_min", 1))
            scale_max = int(q.get("scale_max", 5))
        except (TypeError, ValueError):
            return None, "ค่า scale ต้องเป็นตัวเลข"
        if scale_min >= scale_max:
            return None, "ค่า scale_min ต้องน้อยกว่า scale_max"
        if scale_max - scale_min > 50:
            return None, "ช่วง scale กว้างเกินไป"

    return {
        "type": qtype,
        "text": text,
        "help_text": (q.get("help_text") or "").strip(),
        "options": options,
        "required": bool(q.get("required")),
        "scale_min": scale_min,
        "scale_max": scale_max,
        "scale_label_low": (q.get("scale_label_low") or "").strip(),
        "scale_label_high": (q.get("scale_label_high") or "").strip(),
    }, None


# =========================================================================
# Form list + create
# =========================================================================
@builder_bp.route("/my-forms")
@login_required
def my_forms():
    forms = (
        Form.query.filter_by(user_id=current_user.id)
        .order_by(Form.updated_at.desc())
        .all()
    )
    return render_template("my_forms.html", forms=forms)


@builder_bp.route("/forms/new", methods=["POST"])
@login_required
def new_form():
    title = (request.form.get("title") or "แบบสอบถามไม่มีชื่อ").strip()[:255]
    form = Form(user_id=current_user.id, title=title, description="")
    db.session.add(form)
    db.session.commit()
    flash("สร้างฟอร์มใหม่แล้ว — เพิ่มคำถามได้เลย", "success")
    return redirect(url_for("builder.edit_form", form_id=form.id))


# =========================================================================
# Edit form (GET page) + update meta (POST)
# =========================================================================
@builder_bp.route("/forms/<int:form_id>/edit", methods=["GET", "POST"])
@login_required
def edit_form(form_id):
    form = require_form_ownership(form_id)
    if request.method == "POST":
        form.title = (request.form.get("title") or form.title).strip()[:255]
        form.description = (request.form.get("description") or "").strip()
        db.session.commit()
        flash("บันทึกแล้ว", "success")
        return redirect(url_for("builder.edit_form", form_id=form.id))
    return render_template(
        "edit_form.html",
        form=form,
        qtype_labels=_QTYPE_LABELS_TH,
        question_types=QUESTION_TYPES,
    )


@builder_bp.route("/forms/<int:form_id>/toggle-active", methods=["POST"])
@login_required
def toggle_active(form_id):
    form = require_form_ownership(form_id)
    form.is_active = not form.is_active
    db.session.commit()
    return jsonify({"is_active": form.is_active})


@builder_bp.route("/forms/<int:form_id>/delete", methods=["POST"])
@login_required
def delete_form(form_id):
    form = require_form_ownership(form_id)
    db.session.delete(form)
    db.session.commit()
    flash("ลบฟอร์มแล้ว", "info")
    return redirect(url_for("builder.my_forms"))


# =========================================================================
# Question CRUD (JSON API consumed by builder JS)
# =========================================================================
@builder_bp.route("/api/forms/<int:form_id>/questions", methods=["GET"])
@login_required
def list_questions(form_id):
    require_form_ownership(form_id)
    form = require_form_ownership(form_id)
    return jsonify({"questions": [q.to_dict() for q in form.questions]})


@builder_bp.route("/api/forms/<int:form_id>/questions", methods=["POST"])
@login_required_api
def add_question(form_id):
    form = require_form_ownership(form_id)
    payload = request.get_json(silent=True) or {}
    cleaned, err = _validate_question_payload(payload)
    if err:
        return jsonify({"error": err}), 400

    order_index = (
        db.session.query(db.func.max(Question.order_index))
        .filter_by(form_id=form.id)
        .scalar()
        or 0
    ) + 1

    q = Question(
        form_id=form.id,
        text=cleaned["text"] or "(Section)",
        type=cleaned["type"],
        help_text=cleaned["help_text"],
        options_json=json.dumps(cleaned["options"], ensure_ascii=False),
        required=cleaned["required"],
        order_index=order_index,
        scale_min=cleaned["scale_min"],
        scale_max=cleaned["scale_max"],
        scale_label_low=cleaned["scale_label_low"],
        scale_label_high=cleaned["scale_label_high"],
    )
    db.session.add(q)
    db.session.commit()
    return jsonify(q.to_dict()), 201


@builder_bp.route("/api/forms/<int:form_id>/questions/<int:qid>", methods=["PUT"])
@login_required_api
def update_question(form_id, qid):
    form = require_form_ownership(form_id)
    q = Question.query.filter_by(id=qid, form_id=form.id).first_or_404()
    payload = request.get_json(silent=True) or {}
    cleaned, err = _validate_question_payload(payload)
    if err:
        return jsonify({"error": err}), 400

    q.text = cleaned["text"] or "(Section)"
    q.type = cleaned["type"]
    q.help_text = cleaned["help_text"]
    q.options_json = json.dumps(cleaned["options"], ensure_ascii=False)
    q.required = cleaned["required"]
    q.scale_min = cleaned["scale_min"]
    q.scale_max = cleaned["scale_max"]
    q.scale_label_low = cleaned["scale_label_low"]
    q.scale_label_high = cleaned["scale_label_high"]
    db.session.commit()
    return jsonify(q.to_dict())


@builder_bp.route("/api/forms/<int:form_id>/questions/<int:qid>", methods=["DELETE"])
@login_required_api
def delete_question(form_id, qid):
    form = require_form_ownership(form_id)
    q = Question.query.filter_by(id=qid, form_id=form.id).first_or_404()
    db.session.delete(q)
    db.session.commit()
    return jsonify({"ok": True})


@builder_bp.route("/api/forms/<int:form_id>/reorder", methods=["POST"])
@login_required_api
def reorder_questions(form_id):
    form = require_form_ownership(form_id)
    payload = request.get_json(silent=True) or {}
    order = payload.get("order") or []
    if not isinstance(order, list):
        return jsonify({"error": "order must be a list"}), 400

    questions = {q.id: q for q in form.questions}
    for idx, qid in enumerate(order):
        try:
            qid_int = int(qid)
        except (TypeError, ValueError):
            continue
        if qid_int in questions:
            questions[qid_int].order_index = idx + 1
    db.session.commit()
    return jsonify({"ok": True})


# =========================================================================
# Preview + share link + QR
# =========================================================================
@builder_bp.route("/forms/<int:form_id>/preview")
@login_required
def preview_form(form_id):
    form = require_form_ownership(form_id)
    return render_template("preview_form.html", form=form)


@builder_bp.route("/forms/<int:form_id>/share")
@login_required
def share_form(form_id):
    form = require_form_ownership(form_id)
    base = current_app.config["BASE_URL"].rstrip("/")
    link = f"{base}{url_for('respond.view_form', form_id=form.id)}"
    return render_template("share_form.html", form=form, share_link=link)


@builder_bp.route("/forms/<int:form_id>/qr.png")
@login_required
def form_qr(form_id):
    form = require_form_ownership(form_id)
    import qrcode
    base = current_app.config["BASE_URL"].rstrip("/")
    link = f"{base}{url_for('respond.view_form', form_id=form.id)}"
    img = qrcode.make(link, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
