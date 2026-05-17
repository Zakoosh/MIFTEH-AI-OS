"""Deployment REST API — push, PR, Pages monitoring, live validation."""
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..missions.deployment.push_engine import push_branch
from ..missions.deployment.pr_manager import create_pr, merge_pr
from ..missions.deployment.pages_monitor import get_pages_status, get_latest_deployment
from ..missions.deployment.live_validator import validate_live_url, validate_compliance_pages
from ..missions.deployment.registry_validator import validate_registry
from ..missions.deployment.deploy_pipeline import run_deployment_pipeline

router = APIRouter(prefix="/deployment", tags=["deployment"])

WORKSPACE_ROOT = "/workspaces/MIFTEH-AI-OS"
REGISTRY_PATH = os.path.join(WORKSPACE_ROOT, "targets", "registry.json")

# In-memory deployment history (last 20 reports)
_deployment_history: list = []


def _get_project_config(project_id: str) -> dict:
    """Load project config from registry.json."""
    with open(REGISTRY_PATH) as f:
        registry = json.load(f)
    for p in registry.get("projects", []):
        if p.get("id") == project_id:
            return p
    raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found in registry")


def _resolve_local_path(config: dict) -> str:
    local_path = config.get("local_path", "")
    if local_path.startswith("./"):
        return os.path.join(os.path.dirname(REGISTRY_PATH), local_path[2:])
    return local_path


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
def deployment_status():
    """Overall deployment status across all active projects."""
    try:
        with open(REGISTRY_PATH) as f:
            registry = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="registry.json not found")

    projects = []
    for p in registry.get("projects", []):
        if not p.get("active", False):
            continue
        repo = p.get("repo", "").replace("https://github.com/", "").replace(".git", "")
        pages = get_pages_status(repo) if repo else None
        projects.append({
            "id": p.get("id"),
            "domain": p.get("domain"),
            "pages_url": p.get("pages_url"),
            "pages_status": pages.status if pages else "unknown",
            "pages_url_live": pages.url if pages else None,
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "projects": projects,
        "recent_deployments": _deployment_history[-5:],
    }


# ── Push ──────────────────────────────────────────────────────────────────────

class PushRequest(BaseModel):
    branch: Optional[str] = None
    remote: str = "origin"


@router.post("/{project_id}/push")
def push_project(project_id: str, req: PushRequest):
    """Push branch to remote GitHub repo."""
    config = _get_project_config(project_id)
    repo_path = _resolve_local_path(config)
    branch = req.branch or config.get("branch", "main")

    result = push_branch(repo_path, branch, req.remote)
    return {
        "project_id": project_id,
        "branch": branch,
        "success": result.success,
        "message": result.message,
        "stderr": result.stderr[:500] if result.stderr else "",
    }


# ── PR ────────────────────────────────────────────────────────────────────────

class PRRequest(BaseModel):
    head_branch: Optional[str] = None
    base_branch: str = "main"
    title: Optional[str] = None
    body: Optional[str] = None


@router.post("/{project_id}/pr/create")
def create_project_pr(project_id: str, req: PRRequest):
    """Create a GitHub PR for a project."""
    config = _get_project_config(project_id)
    repo_path = _resolve_local_path(config)
    branch = req.head_branch or config.get("branch", "main")

    result = create_pr(repo_path, branch, req.base_branch, req.title, req.body)
    return {
        "project_id": project_id,
        "success": result.success,
        "pr_url": result.pr_url,
        "pr_number": result.pr_number,
        "message": result.message,
    }


@router.post("/{project_id}/pr/{pr_number}/merge")
def merge_project_pr(project_id: str, pr_number: int, method: str = "squash"):
    """Merge a PR by number."""
    config = _get_project_config(project_id)
    repo_path = _resolve_local_path(config)
    result = merge_pr(repo_path, pr_number, method)
    return {"project_id": project_id, "pr_number": pr_number, **result}


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/{project_id}/pages")
def get_project_pages_status(project_id: str):
    """Get GitHub Pages deployment status."""
    config = _get_project_config(project_id)
    repo = config.get("repo", "").replace("https://github.com/", "").replace(".git", "")
    if not repo:
        raise HTTPException(status_code=400, detail="No repo configured for project")

    status = get_pages_status(repo)
    deployment = get_latest_deployment(repo)
    return {
        "project_id": project_id,
        "pages_status": status.status,
        "pages_url": status.url,
        "source_branch": status.source_branch,
        "updated_at": status.updated_at,
        "latest_deployment": deployment,
    }


# ── Live Validation ───────────────────────────────────────────────────────────

@router.get("/{project_id}/validate/live")
def validate_project_live(project_id: str):
    """HTTP-validate the live production URL."""
    config = _get_project_config(project_id)
    live_url = config.get("domain") or config.get("pages_url", "")
    if not live_url:
        raise HTTPException(status_code=400, detail="No domain or pages_url configured")

    if not live_url.startswith("http"):
        live_url = f"https://{live_url}"

    main_result = validate_live_url(live_url)
    compliance = validate_compliance_pages(live_url)

    return {
        "project_id": project_id,
        "url": live_url,
        "reachable": main_result.reachable,
        "status_code": main_result.status_code,
        "production_signals": {
            "passed": main_result.checks_passed,
            "failed": main_result.checks_failed,
        },
        "production_ready": main_result.ready,
        "compliance_pages": compliance,
        "message": main_result.message,
    }


# ── Registry Validation ───────────────────────────────────────────────────────

@router.get("/registry/health")
def registry_health():
    """Validate all entries in targets/registry.json."""
    results = validate_registry(REGISTRY_PATH)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "registry_path": REGISTRY_PATH,
        "total": len(results),
        "healthy": sum(1 for r in results if r.healthy),
        "projects": [
            {
                "id": r.project_id,
                "healthy": r.healthy,
                "local_path_exists": r.local_path_exists,
                "is_git_repo": r.is_git_repo,
                "remote_url": r.remote_url,
                "branch_exists": r.branch_exists,
                "pages_configured": r.pages_configured,
                "adsense_configured": r.adsense_configured,
                "issues": r.issues,
            }
            for r in results
        ],
    }


# ── Full Pipeline ─────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    branch: Optional[str] = None
    base_branch: str = "main"
    auto_wait_pages: bool = False
    pages_timeout: int = 300


@router.post("/{project_id}/pipeline")
def run_project_pipeline(project_id: str, req: PipelineRequest, background_tasks: BackgroundTasks):
    """Run full deployment pipeline: push → PR → Pages → live validate."""
    config = _get_project_config(project_id)
    repo_path = _resolve_local_path(config)
    branch = req.branch or config.get("branch", "main")
    repo = config.get("repo", "").replace("https://github.com/", "").replace(".git", "")
    live_url = config.get("domain") or config.get("pages_url", "")
    if live_url and not live_url.startswith("http"):
        live_url = f"https://{live_url}"

    report = run_deployment_pipeline(
        project_id=project_id,
        repo_path=repo_path,
        branch=branch,
        github_repo=repo,
        live_url=live_url,
        base_branch=req.base_branch,
        auto_wait_pages=req.auto_wait_pages,
        pages_timeout=req.pages_timeout,
    )

    # Store in history
    report_dict = {
        "project_id": report.project_id,
        "branch": report.branch,
        "timestamp": report.timestamp,
        "push": report.push,
        "pr": report.pr,
        "pages": report.pages,
        "live_validation": report.live_validation,
        "compliance_pages": report.compliance_pages,
        "overall_success": report.overall_success,
        "summary": report.summary,
        "errors": report.errors,
    }
    _deployment_history.append(report_dict)
    if len(_deployment_history) > 20:
        _deployment_history.pop(0)

    return report_dict
