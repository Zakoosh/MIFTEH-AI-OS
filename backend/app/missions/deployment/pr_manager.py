"""Create and manage GitHub PRs via gh CLI."""
import subprocess
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class PRResult:
    success: bool
    pr_url: str
    pr_number: Optional[int]
    message: str


def create_pr(
    repo_path: str,
    head_branch: str,
    base_branch: str = "main",
    title: Optional[str] = None,
    body: Optional[str] = None,
) -> PRResult:
    """Create a PR via gh CLI from head_branch → base_branch."""
    if title is None:
        title = f"feat: deploy {head_branch}"
    if body is None:
        body = (
            f"## Production Deployment\n\n"
            f"Branch `{head_branch}` → `{base_branch}`\n\n"
            f"### Changes\n"
            f"- AdSense monetization activation\n"
            f"- Compliance pages (privacy, terms, cookies, about, contact)\n"
            f"- Production badges and AI-powered banner\n"
            f"- Duplicate title SEO fixes\n\n"
            f"🤖 Deployed by MIFTEH AI OS Pipeline"
        )

    cmd = [
        "gh", "pr", "create",
        "--head", head_branch,
        "--base", base_branch,
        "--title", title,
        "--body", body,
    ]

    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)

    if result.returncode == 0:
        pr_url = result.stdout.strip()
        # Extract PR number from URL
        try:
            pr_number = int(pr_url.rstrip("/").split("/")[-1])
        except ValueError:
            pr_number = None
        return PRResult(success=True, pr_url=pr_url, pr_number=pr_number, message="PR created")
    else:
        stderr = result.stderr.strip()
        # If PR already exists, extract URL from error message
        if "already exists" in stderr or "pull request" in stderr.lower():
            # Try to get the existing PR URL
            view_result = subprocess.run(
                ["gh", "pr", "view", head_branch, "--json", "url,number"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if view_result.returncode == 0:
                data = json.loads(view_result.stdout)
                return PRResult(
                    success=True,
                    pr_url=data["url"],
                    pr_number=data["number"],
                    message="PR already exists",
                )
        return PRResult(success=False, pr_url="", pr_number=None, message=stderr[:300])


def merge_pr(repo_path: str, pr_number: int, method: str = "squash") -> dict:
    """Merge a PR via gh CLI."""
    result = subprocess.run(
        ["gh", "pr", "merge", str(pr_number), f"--{method}", "--auto"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    return {
        "success": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
