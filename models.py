"""SQLAlchemy database models for the survey platform.

Single file for clarity. All tables live in one SQLite db file (survey.db).
"""
from datetime import datetime
import json
import secrets
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def new_public_id():
    """Random URL-safe token for share links (e.g. 'kX3nR9wq_2A').

    Using a token instead of the numeric id means: a new form NEVER gets the
    same link as a deleted one, and the duplicate-submission cookie can't
    collide across forms.
    """
    return secrets.token_urlsafe(8)


# ---- ENUM-ish question type constants ---------------------------------------
QUESTION_TYPES = (
    "multiple",     # radio (pick one) — default, most common
    "checkbox",     # pick many
    "dropdown",     # select one
    "scale",        # linear scale / rating (1..N)
    "short",        # short answer text
    "paragraph",    # long answer text
    "date",         # date picker
    "time",         # time picker
    "section",      # page-break / section header (not a real question)
)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    forms = db.relationship(
        "Form", backref="owner", cascade="all, delete-orphan", lazy="dynamic"
    )

    # ---- Flask-Login -------------------------------------------------------
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Form(db.Model):
    __tablename__ = "forms"
    id = db.Column(db.Integer, primary_key=True)
    # Public share-link token — unique per form, never reused (unlike row ids).
    public_id = db.Column(
        db.String(24), unique=True, index=True, default=new_public_id
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    questions = db.relationship(
        "Question",
        backref="form",
        cascade="all, delete-orphan",
        order_by="Question.order_index",
        lazy=True,
    )
    responses = db.relationship(
        "Response", backref="form", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, include_questions=True):
        data = {
            "id": self.id,
            "public_id": self.public_id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description or "",
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "response_count": self.responses.count(),
        }
        if include_questions:
            data["questions"] = [q.to_dict() for q in self.questions]
        return data


class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey("forms.id"), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    help_text = db.Column(db.Text, default="")
    options_json = db.Column(db.Text, default="[]")  # list of option labels
    required = db.Column(db.Boolean, default=False, nullable=False)
    order_index = db.Column(db.Integer, default=0, nullable=False)
    scale_min = db.Column(db.Integer, default=1)
    scale_max = db.Column(db.Integer, default=5)
    scale_label_low = db.Column(db.String(80), default="")
    scale_label_high = db.Column(db.String(80), default="")

    def to_dict(self):
        return {
            "id": self.id,
            "form_id": self.form_id,
            "text": self.text,
            "type": self.type,
            "help_text": self.help_text or "",
            "options": json.loads(self.options_json) if self.options_json else [],
            "required": bool(self.required),
            "order_index": self.order_index,
            "scale_min": self.scale_min,
            "scale_max": self.scale_max,
            "scale_label_low": self.scale_label_low or "",
            "scale_label_high": self.scale_label_high or "",
        }


class Response(db.Model):
    __tablename__ = "responses"
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey("forms.id"), nullable=False, index=True)
    session_id = db.Column(db.String(120), nullable=False, index=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    answers = db.relationship(
        "Answer", backref="response", cascade="all, delete-orphan", lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "form_id": self.form_id,
            "session_id": self.session_id,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "answers": {a.question_id: a.parsed_value() for a in self.answers},
        }


class Answer(db.Model):
    __tablename__ = "answers"
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey("responses.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False, index=True)
    value_json = db.Column(db.Text, default="")

    def parsed_value(self):
        if not self.value_json:
            return None
        try:
            return json.loads(self.value_json)
        except (ValueError, TypeError):
            return self.value_json


def ensure_form_public_ids():
    """Tiny startup migration: add forms.public_id to pre-existing databases.

    db.create_all() only creates missing TABLES — it never adds new columns to
    tables that already exist. Called from app.py inside an app context, right
    after create_all(). Safe to run every boot (no-ops when already migrated).
    """
    from sqlalchemy import inspect, text

    insp = inspect(db.engine)
    if "forms" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("forms")]
    if "public_id" not in cols:
        db.session.execute(text("ALTER TABLE forms ADD COLUMN public_id VARCHAR(24)"))
        db.session.commit()

    # Backfill any rows without a token (also covers interrupted migrations).
    missing = Form.query.filter(
        (Form.public_id.is_(None)) | (Form.public_id == "")
    ).all()
    if missing:
        used = {t for (t,) in db.session.query(Form.public_id).all() if t}
        for f in missing:
            tok = new_public_id()
            while tok in used:
                tok = new_public_id()
            used.add(tok)
            f.public_id = tok
        db.session.commit()

    # Unique index (works on both SQLite and Postgres).
    db.session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_forms_public_id ON forms (public_id)"
    ))
    db.session.commit()
