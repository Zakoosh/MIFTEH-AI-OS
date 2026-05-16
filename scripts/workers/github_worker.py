"""GitHub worker — checks Actions workflow status via API, detects failed workflows."""
import json
import os
import requests
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
OUTPUT_FILE = SNAPSHOT_DIR / "github_snapshot.json"
GH_API = "https://api.github.com"

# Workflows we care about (file names without .yml)
TRACKED_WORKFLOWS = [
    "ai-analytics-syncer",
    "ai-client-acquisition",
    "ai-kpi-tracker",
    "ai-page-deployer",
    "ai-product-builder",
    "ai-programmatic-seo",
    "ai-revenue-tracker",
    "ai-roi-prioritizer",
    "ai-game-generator",
    "ai-game-testing",
    "ai-game-seo",
    "ai-game-preview",
    "ai-google-indexing",
    "ai-indexing-validation",
    "ai-indexing-retry",
    "ai-daily-reporter",
    "ai-weekly-reporter",
    "ai-runtime-orchestrator",
]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gh_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    h = {"Accept": "application/vnd.github.v3+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get_repo() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        # Try to infer from git remote
        try:
            import subprocess
            out = subprocess.check_output(
                ["git", "remote", "get-url", "origin"], text=True
            ).strip()
            # github.com/owner/repo.git → owner/repo
            if "github.com" in out:
                repo = out.split("github.com/")[-1].replace(".git", "")
        except Exception:
            pass
    return repo


def _fetch_workflow_runs(repo: str, workflow_name: str) -> dict:
    url = f"{GH_API}/repos/{repo}/actions/workflows/{workflow_name}.yml/runs"
    try:
        resp = requests.get(url, headers=_gh_headers(), params={"per_page": 1}, timeout=15)
        if resp.status_code == 200:
            runs = resp.json().get("workflow_runs", [])
            if runs:
                r = runs[0]
                return {
                    "workflow": workflow_name,
                    "status": r.get("status"),
                    "conclusion": r.get("conclusion"),
                    "run_started_at": r.get("run_started_at"),
                    "html_url": r.get("html_url"),
                }
        elif resp.status_code == 404:
            return {"workflow": workflow_name, "status": "not_found", "conclusion": None}
        else:
            return {"workflow": workflow_name, "status": "api_error", "conclusion": None, "http": resp.status_code}
    except Exception as exc:
        return {"workflow": workflow_name, "status": "request_error", "conclusion": None, "error": str(exc)[:100]}


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    repo = _get_repo()
    issues = []
    workflow_states = []

    if not repo:
        snapshot = {
            "worker": "github_worker",
            "timestamp": _now(),
            "status": "degraded",
            "health": "degraded",
            "issues": [{"type": "no_repo", "severity": "warning", "detail": "GITHUB_REPOSITORY not set"}],
            "workflow_states": [],
        }
        OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
        return snapshot

    for wf in TRACKED_WORKFLOWS:
        state = _fetch_workflow_runs(repo, wf)
        workflow_states.append(state)
        if state.get("conclusion") == "failure":
            issues.append({
                "type": "workflow_failed",
                "severity": "critical",
                "detail": f"Workflow '{wf}' last run failed",
                "url": state.get("html_url", ""),
            })
        elif state.get("status") == "not_found":
            issues.append({
                "type": "workflow_missing",
                "severity": "info",
                "detail": f"Workflow '{wf}' not found (may not be deployed yet)",
            })

    failed_count = sum(1 for s in workflow_states if s.get("conclusion") == "failure")
    missing_count = sum(1 for s in workflow_states if s.get("status") == "not_found")
    healthy_count = sum(1 for s in workflow_states if s.get("conclusion") == "success")

    health = "healthy"
    if failed_count >= 3:
        health = "critical"
    elif failed_count >= 1:
        health = "degraded"
    elif missing_count >= len(TRACKED_WORKFLOWS) // 2:
        health = "warning"

    snapshot = {
        "worker": "github_worker",
        "timestamp": _now(),
        "status": "ok",
        "repo": repo,
        "tracked_workflows": len(TRACKED_WORKFLOWS),
        "healthy_count": healthy_count,
        "failed_count": failed_count,
        "missing_count": missing_count,
        "workflow_states": workflow_states,
        "issues": issues,
        "health": health,
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[github_worker] done — {healthy_count} healthy, {failed_count} failed, health={health}")
    return snapshot


if __name__ == "__main__":
    run()
