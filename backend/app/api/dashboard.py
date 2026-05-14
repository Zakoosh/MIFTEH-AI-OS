from __future__ import annotations
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.responses import JSONResponse

router = APIRouter(tags=["dashboard"])

DASHBOARD_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "dashboard"


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def _auth_html(request: Request):
    from ..core.auth import verify_session, SESSION_COOKIE
    token = (request.cookies.get(SESSION_COOKIE)
             or request.headers.get("X-OS-Token")
             or request.headers.get("X-Admin-Token"))
    if not verify_session(token):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=302)
    return None


def _auth_api(request: Request):
    from ..core.auth import verify_session, SESSION_COOKIE
    token = (request.cookies.get(SESSION_COOKIE)
             or request.headers.get("X-OS-Token")
             or request.headers.get("X-Admin-Token"))
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")


# ─── Login / Logout ───────────────────────────────────────────────────────────

@router.get("/admin/os/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request, next: str = "/admin/os"):
    from ..core.auth import verify_session, SESSION_COOKIE, LOGIN_HTML
    if verify_session(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse(url=next, status_code=302)
    html = LOGIN_HTML.format(error_block="", next_url=next)
    return HTMLResponse(content=html)


@router.post("/admin/os/login", include_in_schema=False)
async def login_action(request: Request):
    from ..core.auth import create_session_token, SESSION_COOKIE, LOGIN_HTML
    from ..core.config import get_config
    import urllib.parse
    form = await request.form()
    password = form.get("password", "")
    next_url = form.get("next", "/admin/os")
    cfg = get_config()
    if password != cfg.admin_password:
        html = LOGIN_HTML.format(
            error_block='<div class="err">Incorrect password. Please try again.</div>',
            next_url=next_url,
        )
        return HTMLResponse(content=html, status_code=401)
    token = create_session_token()

    # Cross-origin redirect: if next_url is a different origin, append token as query param
    # so the static YallaPlays dashboard can store it in localStorage for X-OS-Token header auth.
    parsed = urllib.parse.urlparse(next_url)
    is_cross_origin = bool(parsed.scheme and parsed.netloc)
    if is_cross_origin:
        sep = "&" if "?" in next_url else "?"
        redirect_url = f"{next_url}{sep}token={token}"
        return RedirectResponse(url=redirect_url, status_code=302)

    # Same-origin: set cookie as before
    response = RedirectResponse(url=next_url, status_code=302)
    response.set_cookie(
        SESSION_COOKIE, token,
        httponly=True, samesite="lax",
        max_age=8 * 3600,
    )
    return response


@router.get("/admin/os/logout", include_in_schema=False)
async def logout():
    from ..core.auth import SESSION_COOKIE
    response = RedirectResponse(url="/admin/os/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ─── Standalone routes (miftehos.com) ────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page_root(request: Request, next: str = "/"):
    from ..core.auth import verify_session, SESSION_COOKIE, LOGIN_HTML
    if verify_session(request.cookies.get(SESSION_COOKIE) or request.headers.get("X-OS-Token")):
        return RedirectResponse(url=next, status_code=302)
    html = LOGIN_HTML.format(error_block="", next_url=next)
    return HTMLResponse(content=html)


@router.post("/login", include_in_schema=False)
async def login_action_root(request: Request):
    from ..core.auth import create_session_token, SESSION_COOKIE, LOGIN_HTML
    from ..core.config import get_config
    import urllib.parse
    form = await request.form()
    email = form.get("email", "")
    password = form.get("password", "")
    next_url = form.get("next", "/")
    cfg = get_config()
    admin_email = cfg.admin_email or ""
    if (admin_email and email.lower() != admin_email.lower()) or password != cfg.admin_password:
        html = LOGIN_HTML.format(
            error_block='<div class="err">Invalid email or password.</div>',
            next_url=next_url,
        )
        return HTMLResponse(content=html, status_code=401)
    token = create_session_token()
    parsed = urllib.parse.urlparse(next_url)
    is_cross_origin = bool(parsed.scheme and parsed.netloc)
    if is_cross_origin:
        sep = "&" if "?" in next_url else "?"
        return RedirectResponse(url=f"{next_url}{sep}token={token}", status_code=302)
    response = RedirectResponse(url=next_url or "/", status_code=302)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=8 * 3600)
    return response


@router.get("/logout", include_in_schema=False)
async def logout_root():
    from ..core.auth import SESSION_COOKIE
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ─── Dashboard static files ───────────────────────────────────────────────────

@router.get("/admin/os", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard(request: Request):
    redir = _auth_html(request)
    if redir:
        return redir
    index = DASHBOARD_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="Dashboard not built")
    return HTMLResponse(content=index.read_text(), status_code=200)


@router.get("/admin/os/css/{filename}", include_in_schema=False)
async def serve_css(filename: str):
    if ".." in filename:
        raise HTTPException(status_code=400)
    path = DASHBOARD_DIR / "css" / filename
    if not path.exists() or path.suffix != ".css":
        raise HTTPException(status_code=404)
    return FileResponse(str(path), media_type="text/css")


@router.get("/admin/os/js/{filename}", include_in_schema=False)
async def serve_js(filename: str):
    if ".." in filename:
        raise HTTPException(status_code=400)
    path = DASHBOARD_DIR / "js" / filename
    if not path.exists() or path.suffix != ".js":
        raise HTTPException(status_code=404)
    return FileResponse(str(path), media_type="application/javascript")


@router.get("/css/{filename}", include_in_schema=False)
async def serve_css_root(filename: str):
    if ".." in filename:
        raise HTTPException(status_code=400)
    path = DASHBOARD_DIR / "css" / filename
    if not path.exists() or path.suffix != ".css":
        raise HTTPException(status_code=404)
    return FileResponse(str(path), media_type="text/css")


@router.get("/js/{filename}", include_in_schema=False)
async def serve_js_root(filename: str):
    if ".." in filename:
        raise HTTPException(status_code=400)
    path = DASHBOARD_DIR / "js" / filename
    if not path.exists() or path.suffix != ".js":
        raise HTTPException(status_code=404)
    return FileResponse(str(path), media_type="application/javascript")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard_root(request: Request):
    redir = _auth_html(request)
    if redir:
        return redir
    index = DASHBOARD_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="Dashboard not built")
    return HTMLResponse(content=index.read_text(), status_code=200)


# ─── Dashboard data API ───────────────────────────────────────────────────────

@router.get("/api/os/dashboard")
async def get_dashboard_data(request: Request):
    _auth_api(request)
    from ..scheduler.loop_scheduler import get_scheduler
    from ..operations.operation_engine import OperationEngine
    from ..operations.production_runner import ProductionRunner, PREVIEWS_DIR, PR_OUTPUTS_DIR
    from ..core.config import get_config
    from ..scheduler.provider_manager import ProviderCooldownManager
    from ..services.ai_analytics import get_analytics as get_ai_analytics
    from ..services.github_pr_service import GitHubPRService
    import json

    cfg = get_config()
    scheduler = get_scheduler()
    engine = OperationEngine()

    sched_status = scheduler.get_status()
    cooldowns = ProviderCooldownManager()
    provider_health = cooldowns.get_status()
    provider_health["openai"]["configured"] = cfg.openai_active
    provider_health["gemini"]["configured"] = cfg.gemini_active

    all_outputs = engine._memory.get_outputs(limit=100)
    yp_outputs = [o for o in all_outputs if o.get("project") == "yallaplays"]
    fi_outputs = [o for o in all_outputs if o.get("project") == "fionera"]

    pr_files = sorted(PR_OUTPUTS_DIR.glob("*.json"), reverse=True)[:20] if PR_OUTPUTS_DIR.exists() else []
    pr_outputs = []
    for f in pr_files:
        try:
            data = json.loads(f.read_text())
            pr_outputs.append({
                "filename": f.name,
                "project": data.get("project"),
                "output_type": data.get("output_type"),
                "suggested_branch": data.get("suggested_branch"),
                "total_files": data.get("total_files", 0),
                "generated_at": data.get("generated_at"),
                "output_id": data.get("output_id"),
            })
        except Exception:
            pass

    preview_files = sorted(PREVIEWS_DIR.glob("*.html"), reverse=True)[:20] if PREVIEWS_DIR.exists() else []
    previews = [{"filename": f.name, "size_bytes": f.stat().st_size, "url": f"/operations/preview-files/{f.name}"} for f in preview_files]

    activity = []
    for o in sorted(all_outputs, key=lambda x: x.get("created_at", ""), reverse=True)[:20]:
        activity.append({
            "time": o.get("created_at", ""),
            "project": o.get("project"),
            "type": o.get("output_type"),
            "title": o.get("title"),
            "ai_generated": o.get("ai_generated", False),
            "status": o.get("status"),
            "cost_usd": o.get("cost_usd", 0),
        })

    runner = ProductionRunner()
    latest_report = runner.get_latest_report()

    # AI analytics
    ai_analytics = get_ai_analytics(days=7)

    # GitHub PRs
    gh_service = GitHubPRService()
    github_prs = gh_service.list_created_prs(limit=10)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "dashboard_url": cfg.mifteh_os_url,
        "scheduler": sched_status,
        "providers": {
            "openai": provider_health["openai"],
            "gemini": provider_health["gemini"],
            "market_data": {
                "twelve_data": cfg.twelve_data_api_key != "",
                "alpha_vantage": cfg.alpha_vantage_key != "",
            },
            "ai_mode": "ai" if (provider_health["openai"].get("available") or provider_health["gemini"].get("available")) else "template",
            "github_active": cfg.github_active,
        },
        "outputs": {
            "total": len(all_outputs),
            "yallaplays": len(yp_outputs),
            "fionera": len(fi_outputs),
            "ai_generated": sum(1 for o in all_outputs if o.get("ai_generated")),
            "template_generated": sum(1 for o in all_outputs if not o.get("ai_generated")),
            "pending_review": sum(1 for o in all_outputs if o.get("status") in ("generated", "previewed")),
        },
        "repository": {
            "pr_ready": len(pr_outputs),
            "html_previews": len(previews),
            "pr_outputs": pr_outputs[:10],
            "previews": previews[:10],
        },
        "activity": activity,
        "latest_campaign": latest_report,
        "ai_analytics": ai_analytics,
        "github_prs": github_prs,
        "safety": {
            "auto_merge": False,
            "auto_deploy": False,
            "preview_first": True,
            "rollback_enabled": True,
            "validation_required": True,
            "audit_tracking": True,
        },
    }


@router.get("/api/os/loops")
async def get_loops(request: Request):
    _auth_api(request)
    from ..scheduler.loop_scheduler import get_scheduler
    scheduler = get_scheduler()
    return {"loops": scheduler.get_loop_states(), "scheduler_running": scheduler.is_running()}


@router.post("/api/os/loops/{loop_id}/trigger")
async def trigger_loop(loop_id: str, request: Request):
    _auth_api(request)
    from ..scheduler.loop_scheduler import get_scheduler
    scheduler = get_scheduler()
    result = await scheduler.trigger_loop(loop_id)
    return result


@router.post("/api/os/loops/{loop_id}/enable")
async def enable_loop(loop_id: str, request: Request, enabled: bool = True):
    _auth_api(request)
    from ..scheduler.loop_scheduler import get_scheduler
    scheduler = get_scheduler()
    ok = scheduler.set_loop_enabled(loop_id, enabled)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Loop {loop_id} not found")
    return {"loop_id": loop_id, "enabled": enabled}


@router.get("/api/os/provider-health")
async def get_provider_health(request: Request):
    _auth_api(request)
    from ..scheduler.provider_manager import ProviderCooldownManager
    from ..core.config import get_config
    cfg = get_config()
    cooldowns = ProviderCooldownManager()
    status = cooldowns.get_status()
    return {
        "providers": status,
        "openai_configured": cfg.openai_active,
        "gemini_configured": cfg.gemini_active,
        "ai_available": cooldowns.should_use_ai() and (cfg.openai_active or cfg.gemini_active),
        "generation_mode": "ai" if (cooldowns.should_use_ai() and (cfg.openai_active or cfg.gemini_active)) else "template",
    }


@router.get("/api/os/ai-analytics")
async def get_ai_analytics_endpoint(request: Request, days: int = 7):
    _auth_api(request)
    from ..services.ai_analytics import get_analytics
    return get_analytics(days=days)


# ─── GitHub operations ────────────────────────────────────────────────────────

@router.get("/api/os/github/prs")
async def list_github_prs(request: Request):
    _auth_api(request)
    from ..services.github_pr_service import GitHubPRService
    svc = GitHubPRService()
    return {"prs": svc.list_created_prs(limit=20)}


@router.post("/api/os/github/create-pr/{output_id}")
async def create_github_pr(output_id: str, request: Request):
    """Create a real GitHub draft PR from a PR-ready output."""
    _auth_api(request)
    from ..operations.production_runner import PR_OUTPUTS_DIR
    from ..services.github_pr_service import GitHubPRService
    import json

    # Find the output file
    matches = list(PR_OUTPUTS_DIR.glob(f"*{output_id[:8]}*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail=f"PR output for {output_id} not found")

    svc = GitHubPRService()
    result = await svc.create_pr_from_output(matches[0])
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "PR creation failed"))
    return result


@router.post("/api/os/github/create-pr-latest/{project}")
async def create_pr_latest_output(project: str, request: Request):
    """Create a GitHub draft PR from the most recent output for a project."""
    _auth_api(request)
    from ..operations.production_runner import PR_OUTPUTS_DIR
    from ..services.github_pr_service import GitHubPRService

    if project not in ("yallaplays", "fionera"):
        raise HTTPException(status_code=400, detail="Unknown project")

    files = sorted(PR_OUTPUTS_DIR.glob(f"pr_{project}_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail=f"No PR outputs found for {project}")

    svc = GitHubPRService()
    result = await svc.create_pr_from_output(files[0])
    return result
