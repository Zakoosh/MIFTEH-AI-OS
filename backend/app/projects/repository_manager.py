import subprocess
from pathlib import Path

from app.projects.models import RepositoryInfo


def _run_git(repo_path: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def is_git_repo(repo_path: Path) -> bool:
    git_dir = repo_path / ".git"
    return git_dir.is_dir() or git_dir.is_file()


def get_repository_info(repo_path: Path) -> RepositoryInfo:
    if not repo_path.is_dir():
        return RepositoryInfo()

    if not is_git_repo(repo_path):
        return RepositoryInfo(is_git_repo=False)

    branch = _run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])

    status_output = _run_git(repo_path, ["status", "--porcelain"])
    if not status_output:
        status = "clean"
    else:
        changed = len(status_output.strip().split("\n"))
        status = f"{changed} changed files"

    last_commit = _run_git(
        repo_path,
        ["log", "-1", "--format=%h %s", "--no-color"],
    )

    return RepositoryInfo(
        git_branch=branch,
        git_status=status,
        last_commit=last_commit,
        is_git_repo=True,
    )
