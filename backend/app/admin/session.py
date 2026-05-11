import base64
import hmac
import hashlib
import time

from app.admin.config import SESSION_TTL_SECONDS, require_admin_config


def _sign(payload: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_session_token(email: str) -> str:
    _, password = require_admin_config()
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{email}|{expires_at}"
    signature = _sign(payload, password)
    raw_token = f"{payload}|{signature}"
    return base64.urlsafe_b64encode(raw_token.encode("utf-8")).decode("utf-8")


def validate_session_token(token: str | None) -> bool:
    if not token:
        return False

    try:
        email, password = require_admin_config()
        raw_token = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        token_email, expires_at_text, signature = raw_token.rsplit("|", 2)
        expires_at = int(expires_at_text)
    except Exception:
        return False

    if token_email != email:
        return False

    if expires_at < int(time.time()):
        return False

    expected_signature = _sign(f"{token_email}|{expires_at}", password)
    return hmac.compare_digest(signature, expected_signature)
