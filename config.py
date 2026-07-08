import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _load_or_create_secret():
    """Return SECRET_KEY from env, or persist a random one to .secret_key.

    Never ship a hard-coded default: a known key lets anyone forge session
    cookies (and therefore log in as any user).
    """
    env = os.environ.get("SECRET_KEY")
    if env:
        return env
    path = os.path.join(BASE_DIR, ".secret_key")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            val = fh.read().strip()
            if val:
                return val
    val = secrets.token_hex(32)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(val)
        os.chmod(path, 0o600)
    except OSError:
        pass
    return val


class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = _load_or_create_secret()
    # Use DATABASE_URL if provided (e.g. a managed Postgres on the cloud);
    # otherwise fall back to a local SQLite file. Render/Heroku hand out
    # "postgres://" URLs but SQLAlchemy needs the "postgresql://" scheme.
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
        or "sqlite:///" + os.path.join(BASE_DIR, "survey.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- Session / cookie hardening ----------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set FORCE_HTTPS=1 in production so cookies are only sent over TLS.
    SESSION_COOKIE_SECURE = bool(os.environ.get("FORCE_HTTPS"))
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = bool(os.environ.get("FORCE_HTTPS"))
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days
    RESPONDENT_COOKIE_LIFETIME = 60 * 60 * 24 * 365  # 1 year dup-guard

    # Reject oversized request bodies (spam / DoS guard). 2 MB is plenty for a
    # JSON survey submission.
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    # Per-answer limits used by server-side validation.
    MAX_SHORT_LEN = 500
    MAX_PARAGRAPH_LEN = 5000

    # WTF / CSRF
    WTF_CSRF_TIME_LIMIT = None  # token valid for the session lifetime

    # Server base URL used for share links / QR codes.
    # Override with BASE_URL env var in production.
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
