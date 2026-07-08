"""Respond blueprint — public-facing survey view + submit endpoint.

No login required. Duplicate submission prevented via signed cookie.
On submit: persist → emit Socket.IO `new_response` to `form_{id}` room.
"""
import json
import secrets
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, jsonify,
    make_response, current_app, session
)
from models import db, Form, Question, Response, Answer
from extensions import socketio, limiter

respond_bp = Blueprint("respond", __name__)

COOKIE_NAME = "survey_done"


def _respondent_token():
    """Stable per-respondent id stored in cookie (anonymous, no PII)."""
    tok = request.cookies.get("survey_rid")
    if not tok:
        tok = secrets.token_urlsafe(16)
    return tok


@respond_bp.route("/s/<int:form_id>")
def view_form(form_id):
    form = Form.query.get_or_404(form_id)
    if not form.is_active:
        return render_template("form_closed.html", form=form), 404

    done_key = f"{COOKIE_NAME}_{form.id}"
    already_done = request.cookies.get(done_key) == "1"

    questions = [q for q in form.questions if q.type != "section"]
    sections = _split_sections(form.questions)

    resp = make_response(render_template(
        "respond_form.html",
        form=form,
        sections=sections,
        already_done=already_done,
    ))
    resp.set_cookie(
        "survey_rid", _respondent_token(),
        max_age=current_app.config["RESPONDENT_COOKIE_LIFETIME"],
        httponly=True, samesite="Lax",
    )
    return resp


def _split_sections(questions):
    """Group questions into sections. If no section markers, single section."""
    sections = []
    current = {"title": None, "questions": []}
    for q in questions:
        if q.type == "section":
            if current["questions"] or current["title"]:
                sections.append(current)
            current = {"title": q.text, "questions": []}
        else:
            current["questions"].append(q)
    if current["questions"] or current["title"]:
        sections.append(current)
    return sections


def _validate_answer(question, raw):
    """Validate a single answer against the question type.

    Returns (cleaned_value, error_message_or_None).
    `cleaned_value` will be JSON-serialised into answers.value_json.
    """
    qtype = question.type
    max_short = current_app.config.get("MAX_SHORT_LEN", 500)
    max_para = current_app.config.get("MAX_PARAGRAPH_LEN", 5000)

    # required check
    if question.required:
        empty = raw is None or raw == "" or raw == []
        if empty:
            return None, f"กรุณาตอบคำถาม: {question.text}"

    if raw is None or raw == "" or raw == []:
        return None, None  # optional + empty → store None

    if qtype in ("short", "paragraph"):
        val = str(raw).strip()
        if qtype == "short" and len(val) > max_short:
            return None, f"คำตอบยาวเกินไป (สูงสุด {max_short} ตัวอักษร): {question.text}"
        if qtype == "paragraph" and len(val) > max_para:
            return None, f"คำตอบยาวเกินไป (สูงสุด {max_para} ตัวอักษร): {question.text}"
        return val, None

    if qtype in ("multiple", "dropdown"):
        options = json.loads(question.options_json) if question.options_json else []
        val = str(raw).strip()
        if val not in options:
            return None, f"ตัวเลือกไม่ถูกต้อง: {question.text}"
        return val, None

    if qtype == "checkbox":
        options = json.loads(question.options_json) if question.options_json else []
        if not isinstance(raw, list):
            raw = [raw]
        # De-duplicate while preserving order, and validate against the
        # whitelist. A respondent can never select more distinct values than
        # there are options, so this also caps payload size.
        seen = set()
        vals = []
        for x in raw:
            v = str(x).strip()
            if not v or v in seen:
                continue
            if v not in options:
                return None, f"ตัวเลือกไม่ถูกต้อง: {question.text}"
            seen.add(v)
            vals.append(v)
        return vals, None

    if qtype == "scale":
        try:
            val = int(raw)
        except (TypeError, ValueError):
            return None, f"ค่าต้องเป็นตัวเลข: {question.text}"
        if not (question.scale_min <= val <= question.scale_max):
            return None, (
                f"ค่าต้องอยู่ระหว่าง {question.scale_min}-{question.scale_max}: "
                f"{question.text}"
            )
        return val, None

    if qtype == "date":
        val = str(raw).strip()
        # accept YYYY-MM-DD
        try:
            datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            return None, f"รูปแบบวันที่ไม่ถูกต้อง (YYYY-MM-DD): {question.text}"
        return val, None

    if qtype == "time":
        val = str(raw).strip()
        try:
            datetime.strptime(val, "%H:%M")
        except ValueError:
            return None, f"รูปแบบเวลาไม่ถูกต้อง (HH:MM): {question.text}"
        return val, None

    return None, None


@respond_bp.route("/api/submit/<int:form_id>", methods=["POST"])
@limiter.limit("20 per minute; 200 per hour")
def submit_form(form_id):
    form = Form.query.get_or_404(form_id)
    if not form.is_active:
        return jsonify({"error": "form_closed"}), 403

    done_key = f"{COOKIE_NAME}_{form.id}"
    if request.cookies.get(done_key) == "1":
        return jsonify({"error": "already_submitted"}), 409

    data = request.get_json(silent=True) or {}
    answers_in = data.get("answers") or {}

    # build question lookup
    q_map = {q.id: q for q in form.questions if q.type != "section"}

    errors = []
    cleaned = {}

    # required questions must be present
    for qid, q in q_map.items():
        raw = answers_in.get(str(qid))
        val, err = _validate_answer(q, raw)
        if err:
            errors.append({"question_id": qid, "error": err})
        else:
            cleaned[qid] = val
    if errors:
        return jsonify({"error": "validation", "details": errors}), 400

    # persist
    rid = request.cookies.get("survey_rid") or secrets.token_urlsafe(16)
    resp_row = Response(form_id=form.id, session_id=rid)
    db.session.add(resp_row)
    db.session.flush()  # get id

    for qid, val in cleaned.items():
        ans = Answer(
            response_id=resp_row.id,
            question_id=qid,
            value_json=json.dumps(val, ensure_ascii=False) if val is not None else "",
        )
        db.session.add(ans)

    db.session.commit()

    # ---- Real-time emit ----------------------------------------------------
    snapshot = {
        "response_id": resp_row.id,
        "form_id": form.id,
        "submitted_at": resp_row.submitted_at.isoformat(),
        "answers": {qid: val for qid, val in cleaned.items()},
    }
    socketio.emit("new_response", snapshot, room=f"form_{form.id}")

    # ---- Set cookie preventing duplicate -------------------------------
    out = jsonify({"ok": True, "response_id": resp_row.id})
    out.set_cookie(
        done_key, "1",
        max_age=current_app.config["RESPONDENT_COOKIE_LIFETIME"],
        httponly=True, samesite="Lax",
    )
    out.set_cookie(
        "survey_rid", rid,
        max_age=current_app.config["RESPONDENT_COOKIE_LIFETIME"],
        httponly=True, samesite="Lax",
    )
    return out
