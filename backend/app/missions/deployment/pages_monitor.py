"""Poll GitHub Pages deployment status via gh/GitHub API."""
import subprocess
import json
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class PagesStatus:
    status: str          # "built", "building", "errored", "unknown"
    url: Optional[str]
    updated_at: Optional[str]
    source_branch: Optional[str]
    message: str


def get_pages_status(repo: str) -> PagesStatus:
    """Fetch GitHub Pages info for a repo (owner/name format)."""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/pages"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return PagesStatus(
            status="unknown",
            url=None,
            updated_at=None,
            source_branch=None,
            message=result.stderr.strip()[:200],
        )

    try:
        data = json.loads(result.stdout)
        return PagesStatus(
            status=data.get("status", "unknown"),
            url=data.get("html_url"),
            updated_at=data.get("updated_at"),
            source_branch=data.get("source", {}).get("branch"),
            message="ok",
        )
    except json.JSONDecodeError as e:
        return PagesStatus(
            status="unknown",
            url=None,
            updated_at=None,
            source_branch=None,
            message=f"JSON parse error: {e}",
        )


def wait_for_pages_build(
    repo: str,
    timeout_seconds: int = 300,
    poll_interval: int = 15,
) -> PagesStatus:
    """Poll until Pages status is 'built' or timeout reached."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status = get_pages_status(repo)
        if status.status == "built":
            return status
        if status.status == "errored":
            return status
        time.sleep(poll_interval)

    return PagesStatus(
        status="timeout",
        url=None,
        updated_at=None,
        source_branch=None,
        message=f"Pages did not reach 'built' within {timeout_seconds}s",
    )


def get_latest_deployment(repo: str) -> dict:
    """Get the most recent Pages deployment via GitHub deployments API."""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/deployments?environment=github-pages&per_page=1"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip()}

    try:
        deployments = json.loads(result.stdout)
        if deployments:
            return deployments[0]
        return {"error": "no deployments found"}
    except json.JSONDecodeError:
        return {"error": "invalid JSON"}
