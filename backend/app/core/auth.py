from __future__ import annotations
import hashlib
import hmac
import time
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

SESSION_COOKIE = "os_session"
SESSION_TTL = 8 * 3600  # 8 hours


def _secret() -> bytes:
    from .config import get_config
    s = get_config().admin_secret or "mifteh-dev-secret-change-in-production"
    return s.encode()


def create_session_token() -> str:
    ts = str(int(time.time()))
    sig = hmac.new(_secret(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def verify_session(token: str | None) -> bool:
    if not token:
        return False
    try:
        ts_str, sig = token.rsplit(".", 1)
        ts = int(ts_str)
        if time.time() - ts > SESSION_TTL:
            return False
        expected = hmac.new(_secret(), ts_str.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False


def _get_token(request: Request) -> str | None:
    return (
        request.cookies.get(SESSION_COOKIE)
        or request.headers.get("X-OS-Token")
        or request.headers.get("X-Admin-Token")
    )


def require_admin(request: Request) -> None:
    """Dependency for API routes — returns 401 JSON on failure."""
    if not verify_session(_get_token(request)):
        raise HTTPException(status_code=401, detail="Unauthorized. Authenticate at /admin/os/login")


def require_admin_html(request: Request):
    """Dependency for HTML routes — redirects to login on failure."""
    if not verify_session(_get_token(request)):
        raise HTTPException(
            status_code=302,
            headers={"Location": f"/admin/os/login?next={request.url.path}"},
            detail="Redirecting to login",
        )


LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>MIFTEH OS — Sign In</title>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box;}}
    body{{background:#0f172a;color:#f1f5f9;font-family:system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;}}
    .box{{background:#111827;border:1px solid #1e293b;border-radius:12px;padding:36px 40px;width:100%;max-width:380px;}}
    .brand{{font-size:22px;font-weight:800;margin-bottom:4px;}}
    .sub{{font-size:12px;color:#64748b;margin-bottom:28px;}}
    label{{display:block;font-size:12px;font-weight:600;color:#94a3b8;margin-bottom:6px;}}
    input{{width:100%;background:#1e293b;border:1px solid #2d3f5a;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;margin-bottom:16px;outline:none;}}
    input:focus{{border-color:#3b82f6;}}
    button{{width:100%;background:#1d4ed8;color:white;border:none;border-radius:8px;padding:11px;font-size:14px;font-weight:600;cursor:pointer;margin-top:4px;}}
    button:hover{{background:#2563eb;}}
    .err{{color:#ef4444;font-size:12px;margin-bottom:14px;padding:8px 12px;background:#450a0a;border-radius:6px;border:1px solid #991b1b;}}
    .route{{font-size:11px;color:#475569;margin-top:16px;text-align:center;}}
  </style>
</head>
<body>
  <div class="box">
    <div class="brand">MIFTEH OS</div>
    <div class="sub">miftehos.com — AI Operations Platform</div>
    {error_block}
    <form method="POST" action="/login">
      <input type="hidden" name="next" value="{next_url}"/>
      <label>Email</label>
      <input type="email" name="email" placeholder="admin@example.com" autofocus required/>
      <label>Password</label>
      <input type="password" name="password" placeholder="Admin password" required/>
      <button type="submit">Sign In →</button>
    </form>
    <div class="route">Authenticated sessions last 8 hours · MIFTEH OS</div>
  </div>
</body>
</html>"""
