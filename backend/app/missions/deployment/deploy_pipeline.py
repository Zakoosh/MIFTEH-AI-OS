"""End-to-end deployment pipeline: push → PR → Pages monitor → live validate."""
import os
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List

from .push_engine import push_branch, PushResult
from .pr_manager import create_pr, PRResult
from .pages_monitor import get_pages_status, wait_for_pages_build, PagesStatus
from .live_validator import validate_live_url, validate_compliance_pages, LiveValidationResult


@dataclass
class DeploymentReport:
    project_id: str
    branch: str
    timestamp: str
    push: Optional[dict] = None
    pr: Optional[dict] = None
    pages: Optional[dict] = None
    live_validation: Optional[dict] = None
    compliance_pages: Optional[dict] = None
    overall_success: bool = False
    summary: str = ""
    errors: List[str] = field(default_factory=list)


def run_deployment_pipeline(
    project_id: str,
    repo_path: str,
    branch: str,
    github_repo: str,       # "owner/repo" format
    live_url: str,
    base_branch: str = "main",
    auto_wait_pages: bool = True,
    pages_timeout: int = 300,
) -> DeploymentReport:
    """
    Full deployment pipeline:
    1. Push branch to GitHub
    2. Create PR
    3. Optionally wait for Pages to build
    4. Validate live URL
    """
    report = DeploymentReport(
        project_id=project_id,
        branch=branch,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Step 1: Push
    push_result = push_branch(repo_path, branch)
    report.push = {
        "success": push_result.success,
        "message": push_result.message,
        "stderr": push_result.stderr[:500] if push_result.stderr else "",
    }
    if not push_result.success:
        report.errors.append(f"Push failed: {push_result.message}")
        report.summary = "Pipeline stopped: push failed"
        return report

    # Step 2: Create PR
    pr_result = create_pr(repo_path, branch, base_branch)
    report.pr = {
        "success": pr_result.success,
        "pr_url": pr_result.pr_url,
        "pr_number": pr_result.pr_number,
        "message": pr_result.message,
    }
    if not pr_result.success:
        report.errors.append(f"PR creation failed: {pr_result.message}")
        # Non-fatal: push succeeded, PR may need manual creation

    # Step 3: Pages status
    if auto_wait_pages:
        pages_status = wait_for_pages_build(github_repo, timeout_seconds=pages_timeout)
    else:
        pages_status = get_pages_status(github_repo)

    report.pages = {
        "status": pages_status.status,
        "url": pages_status.url,
        "updated_at": pages_status.updated_at,
        "source_branch": pages_status.source_branch,
        "message": pages_status.message,
    }

    # Step 4: Live validation
    live_result = validate_live_url(live_url)
    report.live_validation = {
        "url": live_result.url,
        "reachable": live_result.reachable,
        "status_code": live_result.status_code,
        "checks_passed": live_result.checks_passed,
        "checks_failed": live_result.checks_failed,
        "ready": live_result.ready,
        "message": live_result.message,
    }

    # Step 5: Compliance pages
    compliance = validate_compliance_pages(live_url)
    report.compliance_pages = compliance

    # Overall success
    push_ok = report.push["success"]
    live_ok = live_result.reachable
    compliance_ok = all(v["ok"] for v in compliance.values())

    report.overall_success = push_ok and live_ok
    report.summary = (
        f"Push: {'✓' if push_ok else '✗'} | "
        f"PR: {'✓' if pr_result.success else '~'} | "
        f"Pages: {pages_status.status} | "
        f"Live: {'✓' if live_ok else '✗'} | "
        f"Compliance: {'✓' if compliance_ok else '✗'}"
    )

    return report
