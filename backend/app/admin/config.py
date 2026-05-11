import os
from pathlib import Path


WORKSPACE_ROOT = Path("/workspace").resolve()
DASHBOARD_DIR = WORKSPACE_ROOT / "frontend" / "dashboard"

ADMIN_EMAIL_ENV = "MIFTEH_AI_ADMIN_EMAIL"
ADMIN_PASSWORD_ENV = "MIFTEH_AI_ADMIN_PASSWORD"
SESSION_COOKIE_NAME = "mifteh_ai_admin_session"
SESSION_TTL_SECONDS = 60 * 60 * 8


class AdminConfigError(RuntimeError):
    pass


def get_admin_email() -> str:
    return os.getenv(ADMIN_EMAIL_ENV, "").strip()


def get_admin_password() -> str:
    return os.getenv(ADMIN_PASSWORD_ENV, "")


def admin_auth_configured() -> bool:
    return bool(get_admin_email() and get_admin_password())


def require_admin_config() -> tuple[str, str]:
    email = get_admin_email()
    password = get_admin_password()

    if not email or not password:
        raise AdminConfigError(
            "Admin authentication is not configured. Set MIFTEH_AI_ADMIN_EMAIL and MIFTEH_AI_ADMIN_PASSWORD."
        )

    return email, password
