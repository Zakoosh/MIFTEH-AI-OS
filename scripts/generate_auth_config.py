"""
MIFTEH OS — Auth Config Generator
Generates frontend/dashboard/data/auth_config.json from GitHub secrets.
Called by auth-token-generator.yml workflow (runs daily at midnight UTC).
ADMIN_SECRET never leaves this script — only SHA256/HMAC derivatives are stored.
"""
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def sha256hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def hmac_sha256(key: str, msg: str) -> str:
    return hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()


def main():
    email = os.environ.get("ADMIN_EMAIL", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    secret = os.environ.get("ADMIN_SECRET", "")

    if not email or not password or not secret:
        raise ValueError("ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_SECRET must all be set")

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    # Session expires at end of tomorrow (48h window so rotation doesn't log users out mid-day)
    expires_at = (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=2))

    config = {
        # Hashes for credential verification (one-way — cannot recover original credentials)
        "email_hash": sha256hex(email.strip().lower()),
        "pass_hash": sha256hex(password),
        # HMAC tokens derived from ADMIN_SECRET — rotates daily, prev_token gives grace period
        "token": hmac_sha256(secret, f"mifteh-session:{today}"),
        "prev_token": hmac_sha256(secret, f"mifteh-session:{yesterday}"),
        # Metadata
        "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ttl": 172800,
    }

    out = Path("frontend/dashboard/data/auth_config.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config, indent=2))
    print(f"[auth] Config generated — expires: {config['expires_at']}")
    print(f"[auth] Email hash: {config['email_hash'][:16]}...")
    print(f"[auth] Pass hash:  {config['pass_hash'][:16]}...")
    print(f"[auth] Token:      {config['token'][:16]}...")


if __name__ == "__main__":
    main()
