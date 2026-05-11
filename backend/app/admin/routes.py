from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from app.admin.config import DASHBOARD_DIR, SESSION_COOKIE_NAME, admin_auth_configured, require_admin_config
from app.admin.session import create_session_token, validate_session_token


router = APIRouter(prefix="/admin", tags=["admin"])


def _login_page(error: str = "") -> str:
    error_html = f"<p class='error'>{error}</p>" if error else ""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MIFTEH Admin Login</title>
  <style>
    body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:#07111f; color:#e5eefb; font-family:Arial,sans-serif; }}
    form {{ width:min(420px,92vw); background:#0f172a; border:1px solid #1f2b42; border-radius:20px; padding:28px; }}
    h1 {{ margin:0 0 8px; }}
    p {{ color:#94a3b8; line-height:1.5; }}
    label {{ display:block; margin-top:16px; font-weight:700; }}
    input {{ width:100%; margin-top:8px; padding:12px; border-radius:12px; border:1px solid #334155; background:#0b1220; color:#e5eefb; }}
    button {{ width:100%; margin-top:22px; padding:12px; border:0; border-radius:12px; background:#38bdf8; color:#06101f; font-weight:900; cursor:pointer; }}
    .error {{ color:#fca5a5; }}
  </style>
</head>
<body>
  <form method="post" action="/admin/login">
    <h1>MIFTEH Admin</h1>
    <p>Sign in to access the embedded AI OS operations center.</p>
    {error_html}
    <label>Email<input name="email" type="email" autocomplete="email" required /></label>
    <label>Password<input name="password" type="password" autocomplete="current-password" required /></label>
    <button type="submit">Open AI OS</button>
  </form>
</body>
</html>
"""


def _dashboard_file(relative_path: str = "index.html") -> Path:
    file_path = (DASHBOARD_DIR / relative_path).resolve()
    if DASHBOARD_DIR.resolve() not in file_path.parents and file_path != DASHBOARD_DIR.resolve():
        raise ValueError("Invalid dashboard path")
    return file_path


@router.get("/login")
def admin_login_page():
    return HTMLResponse(_login_page())


@router.post("/login")
async def admin_login(request: Request):
    try:
        configured_email, configured_password = require_admin_config()
    except Exception as exc:
        return HTMLResponse(_login_page(str(exc)), status_code=503)

    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body)
    email = parsed.get("email", [""])[0].strip()
    password = parsed.get("password", [""])[0]

    if email != configured_email or password != configured_password:
        return HTMLResponse(_login_page("Invalid admin credentials."), status_code=401)

    response = RedirectResponse(url="/admin/ai-os/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(email),
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return response


@router.post("/logout")
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/session")
def admin_session(request: Request):
    return {
        "authenticated": validate_session_token(request.cookies.get(SESSION_COOKIE_NAME)),
        "auth_configured": admin_auth_configured(),
        "rbac_ready": True,
        "multi_user_ready": True,
    }


@router.get("/ai-os")
def admin_ai_os_redirect():
    return RedirectResponse(url="/admin/ai-os/", status_code=307)


@router.get("/os")
def admin_os_redirect():
    return RedirectResponse(url="/admin/os/", status_code=307)


@router.get("/ai-os/")
def admin_ai_os_index():
    return FileResponse(_dashboard_file("index.html"))


@router.get("/os/")
def admin_os_index():
    return FileResponse(_dashboard_file("index.html"))


@router.get("/ai-os/{asset_path:path}")
def admin_ai_os_asset(asset_path: str):
    file_path = _dashboard_file(asset_path)
    if not file_path.is_file():
        return JSONResponse(status_code=404, content={"success": False, "error": "Asset not found"})
    return FileResponse(file_path)


@router.get("/os/{asset_path:path}")
def admin_os_asset(asset_path: str):
    file_path = _dashboard_file(asset_path)
    if not file_path.is_file():
        return JSONResponse(status_code=404, content={"success": False, "error": "Asset not found"})
    return FileResponse(file_path)
