"""Push local branch to remote GitHub repo using gh CLI."""
import subprocess
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PushResult:
    success: bool
    branch: str
    remote: str
    message: str
    stderr: str = ""


def push_branch(repo_path: str, branch: str, remote: str = "origin") -> PushResult:
    """Push branch to remote. Uses gh-authenticated git."""
    env = os.environ.copy()

    # Validate path is within targets/
    if "targets/" not in repo_path and not repo_path.startswith("/workspaces/MIFTEH-AI-OS/targets/"):
        return PushResult(
            success=False,
            branch=branch,
            remote=remote,
            message="BLOCKED: repo_path must be within targets/",
        )

    # Verify clean working tree
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        return PushResult(
            success=False,
            branch=branch,
            remote=remote,
            message=f"Uncommitted changes present: {status.stdout.strip()[:200]}",
        )

    # Verify current branch matches
    cur_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if cur_branch.stdout.strip() != branch:
        return PushResult(
            success=False,
            branch=branch,
            remote=remote,
            message=f"Current branch is '{cur_branch.stdout.strip()}', expected '{branch}'",
        )

    result = subprocess.run(
        ["git", "push", remote, branch, "--set-upstream"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode == 0:
        return PushResult(
            success=True,
            branch=branch,
            remote=remote,
            message=f"Pushed {branch} → {remote} successfully",
            stderr=result.stderr,
        )
    else:
        return PushResult(
            success=False,
            branch=branch,
            remote=remote,
            message=f"Push failed (exit {result.returncode})",
            stderr=result.stderr,
        )
